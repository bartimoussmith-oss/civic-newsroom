# Intelligence access and verification

The website's intelligence-publication.json pins data release 5a32d3f5e99bce745898f47673db7dc2ffb16207 in bartimoussmith-oss/civic-newsroom-intelligence-001. The site build copies this descriptor into the deployed website. The browser accepts only that explicitly allowed repository, a commit-pinned data base, and verified file hashes. No data is copied back into the main repository.

The pinned release contains 6,065 generated record representations, 432,020 passages, 7,916 literal identifier mentions and 867,452 unreviewed language candidates. Counts are not counts of independently verified sources, decisions or obligations.

Models and external clients can read intelligence-publication.json, fetch collection.json from base_url, and verify its collection_sha256. collection.json identifies files.json and its hash. The file manifest maps logical paths to ordered physical parts with SHA-256 hashes and byte lengths. Verify parts, concatenate encoded bytes, verify encoded length/hash, decompress only when encoding is gzip, and verify decoded length/hash. Logical JSONL gzip files remain gzip files after this assembly. For SQLite, assemble the database parts in collection.json order, verify database_gzip_sha256, decompress and verify database_sha256.

The workbench provides literal document-token AND search, version-matched per-record graphs, complete graph exports, metadata, logical bulk exports and database parts. UI pagination does not remove entries from complete downloads. Original record access and evidence-selection/media exports remain in the main archive UI.

Deployment is gated on browser retrieval/download checks and rejection of tampered data and unexpected hosts; the same workbench checks run against the deployed URL. Workflow reports and artifacts establish the actual result, not this document alone. These checks do not certify factual accuracy, semantic search, entity resolution, source independence, historical completeness, legal conclusions, Google indexing or AI Mode inclusion.
