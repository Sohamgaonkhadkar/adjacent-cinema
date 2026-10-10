"""Adjacent backend application package.

Day 1 scope: configuration, a strictly validated Qloo client, typed response
models, a fixture-backed mock client, call tracing, and an evidence gate that
can refuse to produce a recommendation.

Milestone 1 scope: the fixture spine — resolution evidence, taste evidence,
candidate-cohort construction, single-normalisation cohort ranking, the evidence
gate, a machine-readable rejection list and an explicit stop state. Still no
live Qloo call, no geography step, no programme bet, no UI.
"""

__version__ = "0.1.0-milestone1"
