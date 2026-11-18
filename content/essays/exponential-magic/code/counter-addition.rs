// Verbatim excerpt from Arcana at 4265da606717b58b983b77d1c3621acf979f223f.
// arcana-core/src/objects.rs, lines 383-387.
// https://github.com/levineuwirth/arcana/blob/4265da606717b58b983b77d1c3621acf979f223f/arcana-core/src/objects.rs#L383-L387
// Excerpt only; imports and surrounding context are omitted.
// MIT license: see ARCANA-LICENSE.txt.

    /// Add `count` counters of `kind`. No-op if `count == 0`.
    pub fn add_counters(&mut self, kind: CounterKind, count: u32) {
        if count == 0 { return; }
        *self.counters.entry(kind).or_insert(0) += count;
    }
