#include "trustline.h"
#include <math.h>
#include <string.h>

static float clamp(float x,float a,float b){return x<a?a:(x>b?b:x);}
static float sq(float x){return x*x;}
int tl_extract(const unsigned char *image,int stride,TLPoint *out){
    int i,x,n=0;
    if(!image||!out||stride<188)return 0;
    for(i=0;i<12;i++){
        int row=(1232-102*i)/11,hist[256]={0},cum=0,lo=0,hi=0,start=-1,m=0;
        float centers[94],threshold,s,span,best=1e9f,cy=0,quality=0;
        const unsigned char *line=image+row*stride;
        for(x=0;x<188;x++)hist[line[x]]++;
        for(x=0;x<256;x++){cum+=hist[x];if(cum>158){lo=x;break;}}
        cum=0;for(x=0;x<256;x++){cum+=hist[x];if(cum>159){hi=x;break;}}
        threshold=fminf(100.f,.46f*(.05f*lo+.95f*hi));
        s=.18f+1.15f*powf((119.f-row)/119.f,1.5f);span=.12f+.65f*s;
        for(x=0;x<=188;x++){
            int dark=x<188&&line[x]<threshold;
            if(dark&&start<0)start=x;
            if(!dark&&start>=0){if(x-start<=14)centers[m++]=.5f*(start+x-1);start=-1;}
        }
        for(x=0;x<m;x++){int j;for(j=x+1;j<m;j++){
            float width=(centers[j]-centers[x])/93.5f*span;
            if(width>.30f&&width<.63f){float score=fabsf(width-.44f);
                if(score<best){best=score;cy=(.5f*(centers[x]+centers[j])-93.5f)/93.5f*span;quality=fmaxf(.1f,1.f-score/.22f);}}
        }}
        if(best<1e8f){out[n].s=s;out[n].y=cy;out[n].quality=quality;n++;}
    }
    return n;
}
/* Gauss-Jordan for the 3x3 normal matrix and its inverse. */
static int inverse(float a[3][3],float inv[3][3]) {
    float z[3][6]; int i,j,k,p;
    for(i=0;i<3;i++)for(j=0;j<6;j++)z[i][j]=j<3?a[i][j]:(j-3==i?1.f:0.f);
    for(i=0;i<3;i++){
        p=i; for(j=i+1;j<3;j++)if(fabsf(z[j][i])>fabsf(z[p][i]))p=j;
        if(fabsf(z[p][i])<1e-7f)return 0;
        for(k=0;k<6;k++){float t=z[p][k];z[p][k]=z[i][k];z[i][k]=t;}
        {float d=z[i][i];for(k=0;k<6;k++)z[i][k]/=d;}
        for(j=0;j<3;j++)if(j!=i){float d=z[j][i];for(k=0;k<6;k++)z[j][k]-=d*z[i][k];}
    }
    for(i=0;i<3;i++)for(j=0;j<3;j++)inv[i][j]=z[i][j+3];
    return 1;
}
static int fit(const TLPoint *p,int n,float c[3],float cov[3][3],float *rms) {
    float w[TL_MAX_POINTS],a[3][3],inv[3][3],b[3],sum=0,err=0;
    int i,j,k,it;
    for(i=0;i<n;i++)w[i]=clamp(p[i].quality,.05f,1.f);
    for(it=0;it<3;it++){
        memset(a,0,sizeof a);memset(b,0,sizeof b);
        for(i=0;i<n;i++){
            float v[3]={1.f,p[i].s,p[i].s*p[i].s};
            for(j=0;j<3;j++){b[j]+=w[i]*v[j]*p[i].y;for(k=0;k<3;k++)a[j][k]+=w[i]*v[j]*v[k];}
        }
        if(!inverse(a,inv))return 0;
        for(j=0;j<3;j++){c[j]=0;for(k=0;k<3;k++)c[j]+=inv[j][k]*b[k];}
        if(it<2)for(i=0;i<n;i++){
            float r=fabsf(p[i].y-c[0]-c[1]*p[i].s-c[2]*sq(p[i].s));
            w[i]=clamp(p[i].quality,.05f,1.f)*(r>.018f?.018f/r:1.f);
        }
    }
    for(i=0;i<n;i++){float r=p[i].y-c[0]-c[1]*p[i].s-c[2]*sq(p[i].s);err+=w[i]*r*r;sum+=w[i];}
    *rms=sqrtf(err/fmaxf(sum,1.f));
    /* Heuristic covariance proxy, NOT a calibrated confidence interval. */
    {float variance=fmaxf(.000016f,err/fmaxf(sum-3.f,1.f));
     for(j=0;j<3;j++)for(k=0;k<3;k++)cov[j][k]=variance*inv[j][k];}
    return 1;
}
void tl_init(TLState *st){if(st){st->previous_k=0;st->blind_time=0;st->has_track=0;}}
TLCommand tl_step(TLState *st,const TLPoint *p,int n,float speed,float dt,int mode){
    TLCommand out={0,0,0,0,0,0,2};
    float c[3],cov[3][3],rms,smax=0,smin=100,q=0;
    float best=1e9f,bestk=0,bestsig=0,bestL=.6f,nominal,curve,vcurve,vvisible;
    int i,j,k;
    if(!st||n<0||n>TL_MAX_POINTS||(!p&&n)||!isfinite(dt)||dt<=0||dt>.2f||!isfinite(speed)||speed<0||mode<0||mode>5)return out;
    for(i=0;i<n;i++){
        if(!isfinite(p[i].s)||!isfinite(p[i].y)||!isfinite(p[i].quality)||p[i].s<=0)return out;
        smax=fmaxf(smax,p[i].s);smin=fminf(smin,p[i].s);q+=clamp(p[i].quality,0,1);
    }
    if(n<4||smax-smin<.15f||!fit(p,n,c,cov,&rms)){
        if(!st->has_track)return out;
        st->blind_time+=dt;
        out.curvature=st->previous_k;
        out.steering=atanf(.26f*out.curvature);
        /* A short hold is shared by all methods; FULL also decays its speed. */
        out.speed=st->blind_time<.18f ? (mode>=2?fmaxf(0,.7f*(1-st->blind_time/.18f)):1.4f):0;
        out.mode=out.speed>0?1:2;return out;
    }
    st->blind_time=0;
    st->has_track=1;
    out.confidence=clamp((n/12.f)*(q/n)*expf(-rms/.035f),0,1);
    nominal=clamp(.25f+.22f*speed,.40f,.75f);
    for(i=0;i<9;i++){
        float L=.35f+.0875f*i,v[3]={1,L,L*L},var=0;
        float y=c[0]+c[1]*L+c[2]*L*L;
        float kap=2*y/(L*L+y*y),gy=2*(L*L-y*y)/sq(L*L+y*y);
        float sigma,cost;
        for(j=0;j<3;j++)for(k=0;k<3;k++)var+=v[j]*cov[j][k]*v[k];
        sigma=fabsf(gy)*sqrtf(fmaxf(0,var));
        /* Candidate preference + uncertainty propagation + extrapolation cost. */
        cost=sq(L-nominal)+.12f*sq(sigma)+3.f*sq(fmaxf(0,L-smax));
        if(mode==TL_NO_RISK)cost=sq(L-nominal)+3.f*sq(fmaxf(0,L-smax));
        if(mode==TL_FIXED||mode==TL_MATCHED_POLICY)cost=sq(L-.6125f);
        if(mode==TL_REGULATED)cost=sq(L-nominal);
        if(cost<best){best=cost;bestk=kap;bestsig=sigma;bestL=L;}
    }
    out.lookahead=bestL;out.curvature=bestk;out.sigma_k=bestsig;
    out.steering=clamp(atanf(.26f*bestk),-.48f,.48f);
    curve=fabsf(2*c[2])/powf(1+c[1]*c[1],1.5f);
    vcurve=sqrtf(1.8f/fmaxf(.25f,fmaxf(fabsf(bestk),curve)));
    out.speed=mode==TL_FIXED?1.4f:fminf(1.8f,vcurve);
    /* d >= v*tau + v^2/(2*a): finite visible-distance braking heuristic. */
    vvisible=-2.f*.12f+sqrtf(sq(2.f*.12f)+4.f*fmaxf(0,smax-.20f));
    if(mode==TL_FULL||mode==TL_NO_RISK||mode==TL_MATCHED_POLICY){
        out.speed=fminf(out.speed,vvisible);
        out.speed*=.45f+.55f*out.confidence;
    }
    out.mode=out.confidence>.5f?0:1;
    st->previous_k=bestk;
    return out;
}
