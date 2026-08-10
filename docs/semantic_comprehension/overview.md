# Semantic Comprehension in Orren

## Overview

The semantic comprehension layer in Orren is responsible for translating
natural-language descriptions into structured `.orn` source files. This
document describes the 12 adversarial categories used in
`tests/test_16_semantic_comprehension.py` and the `examples/natural_language_adversarial/`
suite.

## The 12 Adversarial Categories

| File | Category | Challenge |
|------|----------|-----------|
| 01_ambiguity.orn | Ambiguity | Two equally valid parses of the same description |
| 02_implicit_goals.orn | Implicit Goals | Goals not stated explicitly in the description |
| 03_context_dependent.orn | Context-Dependent | Same description means different things in different contexts |
| 04_contradiction.orn | Contradiction | Internal contradictions within the description |
| 05_human_correction.orn | Human Correction | Corrections applied after initial interpretation |
| 06_unknown_concepts.orn | Unknown Concepts | References to concepts the language doesn't define |
| 07_clarification_required.orn | Clarification Required | Insufficient information to resolve a question |
| 08_multiple_valid_interpretations.orn | Multiple Valid Interpretations | More than one valid semantic graph |
| 09_metaphor_nonliteral.orn | Metaphor / Non-Literal | Metaphorical language that must be grounded |
| 10_cross_domain_reasoning.orn | Cross-Domain Reasoning | Concepts from multiple domains combined |
| 11_intent_preservation.orn | Intent Preservation | Modifications must preserve original intent |
| 12_intent_divergence.orn | Intent Divergence | Two descriptions with different intents |

## Architecture Boundary

Orren is a **language**, not an AI. The semantic comprehension tests verify
that the parser can correctly handle natural-language-like syntax — they
do not test or require any cognitive core, world-model, or autonomous
reasoning. All "comprehension" is achieved through deterministic parsing
rules, not inference or intelligence.

## Test Architecture

`tests/test_16_semantic_comprehension.py` contains 42 tests across 12
adversarial categories plus a `TestArchitectureBoundary` test class that
verifies the parser does not import or invoke any cognitive core, SIR
extension, or world-model.
