# Solver execution adapters

GPMC and Ganak are separately selectable. get_solver_adapter(tool_name)
resolves the chosen transport; execute_solver returns typed SolverResult.
The existing run_wmc tuple return and public tool_name names remain compatible.

GPMC runs with -mode=1 and paired real/imag CNF weights; Ganak runs with
--mode=6 and signed-complex-i weights plus native executable validation.
Neither can silently fall back to the other. Timeouts and process-tree
supervision retain their existing semantics. A nonzero exit is a
SolverExecutionError (RuntimeError); malformed output is a
SolverResultError (ValueError).

Third-party adapters can provide a scoped binary resource, weight grammar
and parser using registered_solver_adapter without modifying the core
check_equivalence dispatch. Numerical weighted counts remain observations,
not exact quantum-equivalence certificates.

This initial Python transport contract does not yet implement the neutral
WmcProblem IR, Rust-side solver adapters, SHA/version evidence or general
cross-backend conformance. Those require separate validation.
