"""The planning layer: specs in, named instructions out, no Blender.

Domain objects compute numbers. Plans turn those numbers into what to build,
what to call it, where to put it and where to measure it. The execution layer
under `scripts/` reads plans and does nothing else — no arithmetic, no literal
sizes, no literal names. That is what lets every number the contracts depend on
be tested on a machine that has never seen `bpy`.
"""
