# Development record

- Initial controller used a longer speed-dependent lookahead; five S-bend runs on development seed 11 showed that it could perform worse than fixed Pure Pursuit. Raw initial results are preserved in `results/initial-development`.
- The nominal lookahead was reduced to `clip(0.25+0.22*v,0.40,0.75)` using development results. Three-track development runs are in `results/development`.
- A startup bug allowing brief forward motion without any past valid fit was corrected; a regression check requires zero speed when no path has ever been observed.
- Scanline extraction was moved from the Python reference into C. Parity is checked for clean and corrupted synthetic frames.
- A preflight evaluation exposed a renderer issue: the selected shadow band changed with the vehicle's position. The final renderer uses a fixed periodic spatial shadow field. Both formal evaluation stages use the corrected renderer. Development artifacts use the earlier renderer and must not be merged with final statistics.
- Evaluation seeds 101–108 were run with frozen controller parameters. The sensitivity penalty did not improve aggregate completion versus `no_risk`. The simpler variant was consequently nominated for a second-stage check.
- Confirmation seeds 201–208 were then run without changing controller or renderer parameters. This stage is the primary report; the first stage remains available in full.
- Demonstrations are selected examples with seed, method and final outcome shown. They are not substituted for the full benchmark.

No claims of winning a competition, real-car deployment, RT1064 frame rate, formal safety or superiority to research MPC/UT methods are supported by this prototype.
