---
name: Plugin Spec Enhancement Proposal
about: Propose a change or addition to the feedBack plugin format
title: "[Proposal] <short title>"
labels: ["proposal"]
---

<!--
See CONTRIBUTING.md for the full process. In short: describe the change and its manifest / loading
shape here, reach rough consensus, then land it as a PR that updates the spec, the schema, an
example, and the CHANGELOG together.
-->

## Summary

<!--
Your elevator pitch: in a sentence or two, and in your own words, say what changes and why it
matters — enough that a reader gets the gist before the detail below. Keep it tight; a wall of
generated text buries the point instead of making it.
-->

## Problem / motivation

What can't a plugin express or do today, or what is awkward? Who needs this?

## Proposed change

What you want to add or change. Be concrete about the **manifest and/or loading behaviour**:

- New / changed **manifest key**(s):
- New / changed **loading or surface behaviour**:
- Example snippet:

```json
// plugin.json fragment
```

## Backward compatibility

- How does an **older Host** behave when it sees a plugin using this? (It should ignore the new
  optional key and still load.)
- Does this remove, rename, or repurpose any existing key? (If so, it's a MAJOR change — explain
  why it's necessary.)

## Version impact

Which bump does this imply?

- [ ] PATCH — wording / clarification / best-practice tweak
- [ ] MINOR — new optional key or behaviour; older Hosts unaffected
- [ ] MAJOR — breaking change to a required key or to existing semantics

## Alternatives considered

Other shapes you weighed, and why this one. (In particular: could a new *optional* key avoid a
breaking change?)
