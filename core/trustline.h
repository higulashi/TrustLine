#ifndef TRUSTLINE_H
#define TRUSTLINE_H
#define TL_MAX_POINTS 16
/* SI units. Vehicle frame: s forward, y left. No heap, OS or camera driver. */
typedef struct { float s, y, quality; } TLPoint;
typedef struct { float previous_k, blind_time; int has_track; } TLState;
typedef struct {
    float steering, speed, lookahead, confidence, sigma_k, curvature;
    int mode; /* 0 tracked, 1 partial/blind, 2 stop */
} TLCommand;
enum { TL_FIXED=0, TL_REGULATED=1, TL_FULL=2, TL_NO_RISK=3, TL_NO_VISIBILITY=4,
       TL_MATCHED_POLICY=5 };
void tl_init(TLState *state);
/* 188x120 grayscale; stride bytes >=188. Output capacity TL_MAX_POINTS.
 * Built-in row calibration is SYNTHETIC; replace for a physical camera. */
int tl_extract(const unsigned char *image, int stride, TLPoint *out);
/* dt seconds, measured_speed m/s. Invalid inputs return stop.
 * mode selects experimental baseline/ablation; FULL is the proposed design. */
TLCommand tl_step(TLState *state, const TLPoint *points, int count,
                  float measured_speed, float dt, int mode);
#endif
