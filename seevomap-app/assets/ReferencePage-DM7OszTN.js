import{t as e}from"./jsx-runtime-BnxRlLMJ.js";import{t}from"./CodeBlock-Ch8Y6u4x.js";import{t as n}from"./DocsShell-C7s1mKEO.js";var r=e(),i=[{title:`Global endpoint override`,desc:`Point the CLI at a custom SeevoMap deployment instead of the default hosted endpoint.`,code:`seevomap --endpoint https://your-space.hf.space search "your query here"`},{title:`seevomap search`,desc:`Search related execution records for a task or technique.`,code:`seevomap search "your query here" --top-k 10`},{title:`seevomap inject`,desc:`Generate prompt-ready context for an agent or experiment loop.`,code:`seevomap inject "improve training stability for small language models" --top-k 12 > context.txt`},{title:`seevomap get`,desc:`Inspect one node or download the full map metadata.`,code:`seevomap get node a30044c5
seevomap get map -o map.json`},{title:`seevomap stats`,desc:`Print graph statistics from the current endpoint.`,code:`seevomap stats`},{title:`seevomap submit`,desc:`Submit one experiment node or batch submit a directory of JSON nodes.`,code:`seevomap submit experiment.json
seevomap submit --dir ./trajectory_nodes/`},{title:`seevomap local`,desc:`Manage private local nodes that should not be uploaded.`,code:`seevomap local add experiment.json
seevomap local list
seevomap local remove abc12345`},{title:`seevomap setup`,desc:`Install the SeevoMap skill into a supported agent tool.`,code:`seevomap setup claude-code
seevomap setup codex`},{title:`seevomap review`,desc:`Maintainer-only commands for inspecting and resolving pending submissions.`,code:`seevomap review --pending --secret "$REVIEW_SECRET"
seevomap review --approve abc12345 --secret "$REVIEW_SECRET"
seevomap review --reject abc12345 --secret "$REVIEW_SECRET"`}];function a(){return(0,r.jsxs)(n,{eyebrow:`Docs / Reference`,title:`CLI and SDK Reference`,summary:`Complete CLI and SDK reference. This page is supporting documentation for the workflow pages, not the primary narrative of the product.`,children:[(0,r.jsxs)(`section`,{className:`surface-card section-tone-stone rounded-3xl p-6 sm:p-8`,children:[(0,r.jsx)(`h2`,{className:`text-2xl font-semibold text-text-primary mb-5`,children:`CLI`}),(0,r.jsx)(`div`,{className:`space-y-6`,children:i.map(e=>(0,r.jsxs)(`div`,{children:[(0,r.jsx)(`h3`,{className:`text-lg font-semibold text-text-primary mb-2`,children:e.title}),(0,r.jsx)(`p`,{className:`text-sm text-text-secondary leading-relaxed mb-3`,children:e.desc}),(0,r.jsx)(t,{code:e.code,language:`bash`})]},e.title))})]}),(0,r.jsxs)(`section`,{className:`surface-card section-tone-sage rounded-3xl p-6 sm:p-8`,children:[(0,r.jsx)(`h2`,{className:`text-2xl font-semibold text-text-primary mb-5`,children:`Python SDK`}),(0,r.jsx)(t,{code:`from seevomap import SeevoMap

svm = SeevoMap()

results = svm.search("optimize transformer pretraining", top_k=5)
context = svm.inject("minimize bits-per-byte under 16MB", top_k=10)
node = svm.get_node("a30044c5")
stats = svm.stats()

svm.submit({
    "task": {"domain": "pretraining", "description": "Parameter Golf"},
    "idea": {"text": "Sliding window eval for bpb measurement"},
    "result": {"metric_name": "val_bpb", "metric_value": 1.1978, "success": True},
})`,language:`python`})]})]})}export{a as default};