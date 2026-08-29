---
title: Search
search: true
---

<div class="search-tabs" role="tablist">
  <button class="search-tab is-active" data-tab="keyword" role="tab" aria-selected="true">Keyword</button>
  <button class="search-tab" data-tab="semantic" role="tab" aria-selected="false">Semantic</button>
</div>

<div class="search-filter-controls">
<button class="library-filter-toggle" aria-expanded="false" aria-controls="search-filters">
Filters<span class="filter-toggle-badge"></span>
</button>
</div>
<div id="search-filters" class="library-filters" hidden>
<div class="filter-row">
<span class="filter-label" data-ep-term="status">status</span>
<div class="filter-options">
<button class="filter-btn filter-status-btn" data-value="draft">draft</button>
<button class="filter-btn filter-status-btn" data-value="working model">working model</button>
<button class="filter-btn filter-status-btn" data-value="durable">durable</button>
<button class="filter-btn filter-status-btn" data-value="refined">refined</button>
<button class="filter-btn filter-status-btn" data-value="superseded">superseded</button>
<button class="filter-btn filter-status-btn" data-value="deprecated">deprecated</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="confidence">confidence</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<input type="number" id="filter-confidence" class="filter-number" min="0" max="100" placeholder="&mdash;" aria-label="Minimum confidence" />
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="importance">importance</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<button class="filter-btn filter-threshold-btn" data-field="importance" data-value="1">1</button>
<button class="filter-btn filter-threshold-btn" data-field="importance" data-value="2">2</button>
<button class="filter-btn filter-threshold-btn" data-field="importance" data-value="3">3</button>
<button class="filter-btn filter-threshold-btn" data-field="importance" data-value="4">4</button>
<button class="filter-btn filter-threshold-btn" data-field="importance" data-value="5">5</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="evidence">evidence</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<button class="filter-btn filter-threshold-btn" data-field="evidence" data-value="1">1</button>
<button class="filter-btn filter-threshold-btn" data-field="evidence" data-value="2">2</button>
<button class="filter-btn filter-threshold-btn" data-field="evidence" data-value="3">3</button>
<button class="filter-btn filter-threshold-btn" data-field="evidence" data-value="4">4</button>
<button class="filter-btn filter-threshold-btn" data-field="evidence" data-value="5">5</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="trust">trust</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<input type="number" id="filter-score" class="filter-number" min="0" max="100" placeholder="&mdash;" aria-label="Minimum trust score" />
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="scope">scope</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<button class="filter-btn filter-ordinal-btn" data-field="scope" data-index="0">personal</button>
<button class="filter-btn filter-ordinal-btn" data-field="scope" data-index="1">average</button>
<button class="filter-btn filter-ordinal-btn" data-field="scope" data-index="2">broad</button>
<button class="filter-btn filter-ordinal-btn" data-field="scope" data-index="3">civilizational</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="novelty">novelty</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<button class="filter-btn filter-ordinal-btn" data-field="novelty" data-index="0">conventional</button>
<button class="filter-btn filter-ordinal-btn" data-field="novelty" data-index="1">moderate</button>
<button class="filter-btn filter-ordinal-btn" data-field="novelty" data-index="2">idiosyncratic</button>
<button class="filter-btn filter-ordinal-btn" data-field="novelty" data-index="3">innovative</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="practicality">practicality</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<button class="filter-btn filter-ordinal-btn" data-field="practicality" data-index="0">abstract</button>
<button class="filter-btn filter-ordinal-btn" data-field="practicality" data-index="1">moderate</button>
<button class="filter-btn filter-ordinal-btn" data-field="practicality" data-index="2">high</button>
<button class="filter-btn filter-ordinal-btn" data-field="practicality" data-index="3">exceptional</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label" data-ep-term="stability">stability</span>
<div class="filter-options">
<span class="filter-prefix">&ge;</span>
<button class="filter-btn filter-ordinal-btn" data-field="stability" data-index="0">volatile</button>
<button class="filter-btn filter-ordinal-btn" data-field="stability" data-index="1">revising</button>
<button class="filter-btn filter-ordinal-btn" data-field="stability" data-index="2">fairly stable</button>
<button class="filter-btn filter-ordinal-btn" data-field="stability" data-index="3">stable</button>
<button class="filter-btn filter-ordinal-btn" data-field="stability" data-index="4">established</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label">archive</span>
<div class="filter-options">
<button class="filter-btn filter-archive-mode-btn" data-value="exclude" title="Hide archived-copy pages from results">exclude</button>
<button class="filter-btn filter-archive-mode-btn" data-value="only" title="Show only archived-copy pages">only</button>
</div>
</div>
<div class="filter-row">
<span class="filter-label">link status</span>
<div class="filter-options">
<button class="filter-btn filter-archive-status-btn" data-value="live">live</button>
<button class="filter-btn filter-archive-status-btn" data-value="moved">moved</button>
<button class="filter-btn filter-archive-status-btn" data-value="rotted">rotted</button>
<button class="filter-btn filter-archive-status-btn" data-value="error">error</button>
</div>
</div>
<div class="filter-row filter-row-actions">
<button class="filter-clear-btn">Clear all</button>
</div>
</div>

<div id="search" class="search-panel is-active" data-panel="keyword"></div>
<p id="search-timing" aria-live="polite"></p>

<div class="search-panel" data-panel="semantic">
  <input id="semantic-query" class="semantic-query-input" type="search"
         placeholder="Describe what you're looking for…" autocomplete="off" spellcheck="false">
  <p id="semantic-status" class="semantic-status" aria-live="polite"></p>
  <div id="semantic-results"></div>
</div>
