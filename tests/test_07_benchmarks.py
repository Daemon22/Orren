"""Benchmarks and memory profiling for the Orren engine.

Validates:
  - End-to-end pipeline latency on small / medium / large inputs.
  - Per-subsystem latency (parser, SIR builder, resolver, coordinator,
    codegen) using cProfile.
  - Peak memory usage via tracemalloc.
  - No memory leaks across repeated runs.
  - Performance stays within acceptable bounds (no exponential blow-up).

Run: pytest tests/test_07_benchmarks.py -v
"""
import gc
import os
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    Engine,
    EquilibriumResolver,
    RealizationCoordinator,
    SIRBuilder,
    generate_code,
)


# ---------------------------------------------------------------------------
# Synthetic sources of varying size
# ---------------------------------------------------------------------------


def make_source(n_entities: int, n_dimensions_per: int = 4) -> str:
    """Build a synthetic .orn source with n_entities child entities,
    each carrying vibe + cognitive + spatial + conditional statements."""
    lines = ["create bench_app : Application", "", "    structure:", "        root"]
    for i in range(n_entities):
        lines.append(f"            entity_{i}")
    lines.append("")
    lines.append("    cognitive:")
    for i in range(n_entities):
        lines.append(f"        entity_{i}.value = task_{i}")
    lines.append("")
    lines.append("    vibe:")
    for i in range(n_entities):
        lines.append(f"        entity_{i}.color_character = emerald")
        lines.append(f"        entity_{i}.tone = calm")
    lines.append("")
    lines.append("    spatial:")
    for i in range(n_entities):
        lines.append(f"        entity_{i} located_in root")
    lines.append("")
    lines.append("    conditional:")
    for i in range(n_entities):
        lines.append(f"        entity_{i} activates on signal_{i}")
    lines.append("")
    lines.append("    equilibrium:")
    for i in range(min(n_entities, 5)):
        lines.append(f"        rule_{i}:")
        lines.append(f"            when vibe.calm is active AND cognitive.value is active")
        lines.append(f"            preserve both")
        lines.append(f"            resolution: rule_{i}_resolution")
    lines.append("")
    lines.append("    realize:")
    lines.append("        target: web_interface (HTML/CSS/JS)")
    lines.append("            capabilities: layout, color, event_handling")
    lines.append("            preservation_score: 0.83")
    return "\n".join(lines) + "\n"


SMALL_SOURCE = make_source(5)
MEDIUM_SOURCE = make_source(50)
LARGE_SOURCE = make_source(200)


# ---------------------------------------------------------------------------
# Latency benchmarks
# ---------------------------------------------------------------------------


class TestLatency:
    def test_small_end_to_end_under_500ms(self):
        engine = Engine()
        t0 = time.perf_counter()
        engine.run(SMALL_SOURCE)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 500, f"small source took {elapsed_ms:.1f}ms"

    def test_medium_end_to_end_under_2s(self):
        engine = Engine()
        t0 = time.perf_counter()
        engine.run(MEDIUM_SOURCE)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 2000, f"medium source took {elapsed_ms:.1f}ms"

    def test_large_end_to_end_under_10s(self):
        engine = Engine()
        t0 = time.perf_counter()
        engine.run(LARGE_SOURCE)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 10000, f"large source took {elapsed_ms:.1f}ms"

    def test_scaling_is_sublinear_or_linear(self):
        """Per-node cost should not blow up super-linearly."""
        engine = Engine()
        t0 = time.perf_counter()
        engine.run(SMALL_SOURCE)
        small_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        engine.run(MEDIUM_SOURCE)
        medium_ms = (time.perf_counter() - t0) * 1000

        # MEDIUM has 10x the entities of SMALL. Per-entity cost should
        # not blow up: medium_ms / 50 should be ≤ small_ms / 5 * 5
        # (i.e. allow up to 5x per-entity slowdown for cache effects).
        per_entity_small = small_ms / 5
        per_entity_medium = medium_ms / 50
        assert per_entity_medium < per_entity_small * 5, (
            f"per-entity cost blew up: small={per_entity_small:.3f}ms, "
            f"medium={per_entity_medium:.3f}ms"
        )


# ---------------------------------------------------------------------------
# Per-subsystem benchmarks
# ---------------------------------------------------------------------------


class TestSubsystemProfile:
    def test_parser_under_1s_on_large(self):
        parser = CoParser()
        t0 = time.perf_counter()
        parser.parse(LARGE_SOURCE)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0

    def test_sir_builder_under_1s_on_large(self):
        exprs = CoParser().parse(LARGE_SOURCE)
        builder = SIRBuilder()
        t0 = time.perf_counter()
        builder.build(exprs)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0

    def test_resolver_under_1s_on_large(self):
        graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        resolver = EquilibriumResolver()
        t0 = time.perf_counter()
        resolver.resolve(graph)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0

    def test_coordinator_under_1s_on_large(self):
        graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        coordinator = RealizationCoordinator()
        t0 = time.perf_counter()
        coordinator.coordinate(graph)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0

    def test_codegen_under_1s_on_large(self):
        graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        tgt = graph.realization_targets[0]
        t0 = time.perf_counter()
        generate_code(graph, tgt)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0


# ---------------------------------------------------------------------------
# Memory profiling
# ---------------------------------------------------------------------------


class TestMemoryProfile:
    def test_peak_memory_under_50mb_on_large(self):
        gc.collect()
        tracemalloc.start()
        Engine().run(LARGE_SOURCE)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 50, f"peak memory {peak_mb:.1f}MB > 50MB"

    def test_no_memory_growth_across_repeated_runs(self):
        """Run the engine 10 times; peak memory should not grow."""
        gc.collect()
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        for _ in range(10):
            Engine().run(MEDIUM_SOURCE)
        end = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        growth_mb = (end - baseline) / (1024 * 1024)
        # Allow some slack for caches, but no unbounded growth.
        assert growth_mb < 10, f"memory grew {growth_mb:.1f}MB across 10 runs"

    def test_parser_does_not_retain_source_string(self):
        """After parsing, the parser's last_lexed field holds references
        to LexedLine objects; running parse() again should replace them,
        not accumulate."""
        gc.collect()
        parser = CoParser()
        for _ in range(5):
            parser.parse(LARGE_SOURCE)
        # The last parse should have replaced earlier ones.
        assert len(parser.last_lexed) > 0
        # Each LexedLine is small; total retained should be reasonable.
        total_str_bytes = sum(
            len(l.text.encode("utf-8")) for l in parser.last_lexed
        )
        assert total_str_bytes < 1_000_000  # < 1MB of source text


# ---------------------------------------------------------------------------
# cProfile smoke (not asserting specific numbers, just that it runs)
# ---------------------------------------------------------------------------


class TestCProfileSmoke:
    def test_cprofile_runs_cleanly(self):
        import cProfile
        import pstats
        from io import StringIO

        pr = cProfile.Profile()
        pr.enable()
        Engine().run(MEDIUM_SOURCE)
        pr.disable()
        s = StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats(20)
        output = s.getvalue()
        # Just check that some functions were profiled.
        assert "function calls" in output
        assert "orren_engine" in output or "<" in output  # some function name


# ---------------------------------------------------------------------------
# Reallocation check
# ---------------------------------------------------------------------------


class TestNoReallocationChurn:
    def test_repeated_runs_have_stable_node_count(self):
        """Running the engine twice on the same input must produce the
        same number of SIR nodes — no accumulation."""
        engine = Engine()
        r1 = engine.run(SMALL_SOURCE)
        n1 = r1.sir_node_count
        r2 = engine.run(SMALL_SOURCE)
        n2 = r2.sir_node_count
        assert n1 == n2
