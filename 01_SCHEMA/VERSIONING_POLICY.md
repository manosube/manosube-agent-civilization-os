# Schema Versioning Policy v0.1

Schema IDs use `https://schemas.manosube.org/agent-civilization-os/v0.1/{schema-path}`. Records carry `schema_version: "0.1"`. Unknown IDs, dialects, or versions are rejected. Adding an optional field is compatible only when meaning and canonical bytes remain unchanged; changing required fields, enums, normalization, identity, authority, or fingerprint semantics is breaking. Silent upgrade and coercion are prohibited.
