# Public-record intelligence engine

This is a concrete retrieval/evidence layer, not a claim of Palantir-equivalent capability or automatic investigative truth. It reads only the separately published documents/ and meetings/ representation corpus, validates hashes and preserves input source/version identities. Internal research is not crawled.

Capabilities: SQLite FTS5 passage retrieval with BM25 ranking; exact Unicode character spans and evidence packets; document metadata; literal ordinance/resolution/contract/PUDC reference groups; decision, commitment, date and amount language candidates; exact normalized-text families; a partitioned static document-token index and portable graph/JSONL exports. No paid AI, LLM inference or private data import.

Commands:
python -m unittest discover -s intelligence -p 'test_engine.py' -v
python intelligence/engine.py build --dataset-repo PATH_TO_DATA_REPO --out FRESH_OUTPUT --revision CODE_REVISION
python intelligence/engine.py search --db FRESH_OUTPUT/intelligence.sqlite --query annexation
python intelligence/engine.py packet --db FRESH_OUTPUT/intelligence.sqlite --passage-id PASSAGE_ID

Full-text token queries use AND over literal normalized words, not semantic reasoning. Static posting values index public records.json. Match scores are not factual confidence. Exact-text families can include boilerplate and do not establish independent sources. Dates from paths are unverified labels. References have unresolved namespaces. A paragraph containing approved, shall, a dollar figure or a date does not establish adoption, an enforceable obligation, payment or an event date. All such analytical outputs are explicitly unreviewed candidates. Wrapper sections preceding a Markdown separator are indexed for access but excluded from candidate extraction; remaining sections still require original-source review.

The workflow runs fixtures and a real-corpus retrieval/evidence-packet smoke check before committing bounded derived outputs. intelligence-publication.json identifies a pinned output commit. It does not repair GitHub Pages account permissions, integrate all intelligence controls into the existing browser UI, copy original PDFs, establish exhaustive historical coverage, or automatically write media findings. Those are separate remaining tasks. Database parts concatenate into one gzip stream before decompression; JSONL/graph/token exports are separately available.
