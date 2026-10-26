# Civic Newsroom agent rules

Mission: a public, issue-centered historical municipal newsroom with complete traceable source access and multi-format evidence-linked publishing. Work here, not destructively in upstream repos. Existing source repos are read-only inputs; preserve their histories, IDs and originals.

Separate code, normalized public datasets, candidate issue memberships and editorial findings. Use versioned manifests and content hashes. Repository creation is not integration; passing syntax tests is not a verified deployment. Keep unmatched, excluded, partial and failed sources visible. Do not claim every historical issue is discovered.

No private content, credentials or personal casework in public output. No automatic accusation or source-independence inference. Publication approval is separate from extraction. No paid services, repo creation, cross-repo writes, merges or production deployment without the platform's required exact-action approval. General encouragement does not bypass that gate.

Data partitions belong in civic-newsroom-data-NNN repositories after review. Bound file/repository/site sizes, record measured bytes, and use a root manifest; do not clone all partitions into one Pages artifact. Match IDs and source spans across tools. Code may reuse pinned tested upstream components rather than duplicate them.

First pipeline: scripts/build_data.py consumes an explicitly approved generated public mirror. Workflow outputs are review artifacts, not published datasets or a finished newsroom. Next: review outputs, publish approved versioned partitions, implement browser manifest resolution, topic discovery/review and media production, then verify actual live results.
