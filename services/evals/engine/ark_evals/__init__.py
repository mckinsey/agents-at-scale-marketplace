"""ark_evals — a one-shot evaluation engine for Ark agentic workflows.

Reads the output an Ark/Argo workflow produced, grades it against a suite of
golden cases (structural / exact / judge), and writes a Markdown report with a
pass rate against the suite threshold. Invoked as the final step of a workflow
via an Argo ``onExit`` handler; the judge is an Ark ``Model`` called through an
Ark ``Query`` so judge calls are traced like any other model call.

The grading mechanics (judge parsing, per-dimension pass rules) are adapted
from the internal ``agentic-evals-service``; the transport (read a produced
file, judge via an Ark Query) is Ark-native and specific to this add-on.
"""

__version__ = "0.1.0"
