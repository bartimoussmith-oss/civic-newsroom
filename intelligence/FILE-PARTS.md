# Logical-file storage repair

Observed failure in run 40286406710: ValueError: Intelligence file needs further partitioning. The repair does not assume a specific offending filename and does not lower a size guard or drop records.

file_parts.py calls the original evidence engine, permits packaging only after a complete collection marker and database record count exist, and recovers only the two explicit generated-output size exceptions. Integrity, schema, input and other failures are not bypassed. It replaces only newly generated derived files with reversible gzip/parts when needed. files.json maps logical names to physical parts, encoded and decoded lengths/hashes. collection.json identifies and hashes that manifest. All logical files are reconstructed and verified before publication.

The browser reconstructs the same bytes and verifies all layers before parsing. Native gzip decompression is required only for gzip-encoded logical JSON; unsupported browsers receive an explicit error and can use an external manifest-aware client. Bulk logical JSONL gzip streams remain downloadable in their original logical format after reconstruction. Source Markdown, normalized source blobs, original repositories and source-version identities are not modified.

Publication keeps the 45 MiB per-file and 256 MiB derived-output guards. If an aggregate guard still fails, measured sizes must guide allocation of a separate approved data host. A passed packaging test is not factual validation, semantic search, verified entity resolution, a certified decision timeline, complete historical coverage or live-site deployment. GitHub Pages setup and Google indexing remain separate gates.
