# References and attribution

Mathematical methods and related designs are listed below. MIT applies to this repository's source, not to the linked works.

1. R. C. Coulter, *Implementation of the Pure Pursuit Path Tracking Algorithm*, CMU-RI-TR-92-01, 1992. [CMU publication page](https://www.ri.cmu.edu/publications/implementation-of-the-pure-pursuit-path-tracking-algorithm/). Foundational geometric controller; not an original contribution here.
2. Atsushi Sakai and contributors, [PythonRobotics Pure Pursuit example](https://github.com/AtsushiSakai/PythonRobotics/blob/master/PathTracking/pure_pursuit/pure_pursuit.py). Educational reference for path tracking and bicycle simulations; no source copied.
3. S. Macenski, S. Singh, F. Martin, J. Gines, *Regulated Pure Pursuit for Robot Path Tracking*, Autonomous Robots, 2023. [Paper](https://arxiv.org/abs/2305.20026), [official implementation](https://github.com/ros-navigation/navigation2/tree/main/nav2_regulated_pure_pursuit_controller). Adaptive lookahead and curvature/proximity speed regulation already exist. Our `regulated` baseline is a small local implementation of two ideas, **not a reproduction of Nav2 RPP**; it omits collision checking, costmaps, and other Nav2 features.
4. Chinnawut Nantabut, *Unscented Transform-based Pure Pursuit Path-Tracking Algorithm under Uncertainty*, 2024. [Paper](https://arxiv.org/abs/2409.18585). Prior uncertainty-aware Pure Pursuit work; this project uses a first-order sensitivity proxy rather than an unscented transform. No experimental comparison to that method is claimed.
5. Jelena Trisovic, Andrea Carron, Melanie N. Zeilinger, *Predictive Control for Driving under Uncertain Road Geometry Estimated from Onboard Vision*, arXiv:2508.02494, v2, 2026 (v1 title: *Uncertainty-Aware Perception-Based Control for Autonomous Racing*). [Paper](https://arxiv.org/abs/2508.02494). Prior perception-to-control uncertainty propagation via scenario MPC; TrustLine does not implement or outperform this research method.
6. Dongkwon Jin et al., *OMR: Occlusion-Aware Memory-Based Refinement for Video Lane Detection*, ECCV 2024. [Official source](https://github.com/dongkwonjin/OMR). Shows that occlusion-aware lane memory is an existing research topic, not a new claim here.
7. NXP, [i.MX RT1064 product information](https://www.nxp.com/products/i.MX-RT1064). Hardware background only; no on-board test has been performed.

The experiments compare the six local variants described in the report. They do not evaluate the UT or scenario-MPC methods listed above.
