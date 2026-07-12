# Integration and release verification

The executable v2 integration coverage lives in the top-level pytest modules:

- three-host render and adapter equivalence;
- clean installation and ownership-safe v1 replacement;
- project migration, crash recovery, and concurrent first write;
- evidence append/resolve, supersession, quarantine, and snapshots;
- workflow policy and retention behavior;
- reading-list, full paper, and full patent fixture flows across all three hosts.

`v2_flow.py` is the deterministic fixture harness used by `test_v2_e2e.py`. Fixture
contracts live under `tests/fixtures/e2e/` and compare action/output behavior rather than
host-specific prompt text. Running-agent model behavior remains a separate release smoke
test because it is nondeterministic and may require network access.

Release verification additionally builds a wheel, installs it into a clean environment,
runs console scripts from outside the repository, validates the Claude plugin, and tests
Python 3.10 through 3.12 on macOS and Ubuntu. Network retrieval and live model behavior
remain external smoke tests; the core and renderer have no MCP dependency.
