# Search and AI Mode release gates

Intended site: https://bartimoussmith-oss.github.io/civic-newsroom/ . This document does not establish that it is live, indexed or selected by Google.

1. Enable GitHub Pages for this repository with GitHub Actions as the source, using owner-authorized settings. Workflow tokens previously could not create the Pages site. No code change alone removes that permission requirement.
2. Require source hash checks, real browser record/media tests and no-JavaScript static-page tests.
3. Verify the exact public application revision, full-text record pages, canonical URLs, archive/topic links and sitemap. Check origin-level robots access and indexing headers.
4. Use an owner-verified Google Search Console URL-prefix property to submit the sitemap and inspect representative and coverage URLs. No Search Console authentication or submission is implemented here.
5. Record deployment, crawling, indexing, canonical selection and AI Mode appearance separately. A successful deployment is not indexing; a site: query is not a complete coverage audit.

Google says AI supporting pages must be indexed and snippet-eligible and that no special AI files or schema are required. Crawling/indexing/serving are not guaranteed. Crawl requests can take days to weeks, with no guarantee of eventual indexing. No AI Mode inclusion date or complete-corpus reasoning guarantee can be promised. llms.txt and structured exports are convenience formats, not an indexing guarantee.

The available corpus is generated public representations. It is not certified as every original historical record. Internal research, media commentary, private holdings and advocacy drafts remain outside the supported publication inputs.
