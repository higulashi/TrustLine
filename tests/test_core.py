import math
import unittest
import numpy as np
from trustline.native import Controller
from trustline.simulator import Vehicle,render,run,slope,center
from trustline.vision import extract,extract_reference

class CoreTests(unittest.TestCase):
    def test_straight_and_symmetry(self):
        straight=[(float(s),0,1) for s in np.linspace(.2,1.25,12)]
        out=Controller().step(straight,1)
        self.assertAlmostEqual(out.steering,0,places=5)
        self.assertGreater(out.speed,1)
        for sign in (-1,1):
            p=[(s,sign*.08,1) for s,_,_ in straight]
            o=Controller().step(p,1)
            self.assertGreater(o.steering*sign,0)
            self.assertLessEqual(abs(o.steering),.48+1e-6)
    def test_blind_stop_and_recovery(self):
        ctl=Controller();points=[(float(s),.03,1) for s in np.linspace(.2,1.2,12)]
        ctl.step(points,1)
        for _ in range(12):out=ctl.step([],1)
        self.assertEqual(out.speed,0)
        self.assertEqual(out.mode,2)
        self.assertGreater(ctl.step(points,0).speed,0)
    def test_invalid_and_degenerate(self):
        for p in ([(.4,.1,1)]*12,[(.2,float('nan'),1)]*12):
            self.assertEqual(Controller().step(p,1).speed,0)
        self.assertEqual(Controller().step([],1,dt=0).speed,0)
    def test_outlier_resistance(self):
        points=[(float(s),.04+.1*s,1) for s in np.linspace(.2,1.2,12)]
        original=Controller().step(points,1)
        points[5]=(points[5][0],points[5][1]+.25,1)
        corrupt=Controller().step(points,1)
        self.assertLess(abs(original.steering-corrupt.steering),.06)
    def test_renderer_and_extractor(self):
        v=Vehicle(yaw=math.atan(slope(0,'s_bend')))
        image=render(v,'s_bend','clean',0,11)
        self.assertEqual(image.shape,(120,188))
        self.assertGreaterEqual(len(extract(image)),8)
        np.testing.assert_allclose(extract(image),extract_reference(image),atol=2e-6)
    def test_closed_loop_determinism(self):
        a,_=run(max_time=.2);b,_=run(max_time=.2)
        self.assertEqual(a,b)
    def test_extractor_parity_under_corruption(self):
        for scenario in ('shadow','dropout','distractor','mixed'):
            for x in (0.,1.,3.):
                v=Vehicle(x=x,y=float(center(x,'s_bend')),yaw=math.atan(slope(x,'s_bend')))
                image=render(v,'s_bend',scenario,1.24,11)
                np.testing.assert_allclose(extract(image),extract_reference(image),atol=2e-6)

if __name__=='__main__':unittest.main()
