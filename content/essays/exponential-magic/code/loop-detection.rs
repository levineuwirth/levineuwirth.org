// Verbatim excerpt from Arcana at 4265da606717b58b983b77d1c3621acf979f223f.
// arcana-core/src/engine.rs, lines 152-165.
// https://github.com/levineuwirth/arcana/blob/4265da606717b58b983b77d1c3621acf979f223f/arcana-core/src/engine.rs#L152-L165
// Excerpt only; imports and surrounding context are omitted.
// MIT license: see ARCANA-LICENSE.txt.

fn detect_and_mark_loop_draw(state: &mut GameState) {
    if state.result.is_some() {
        return;
    }
    let fp = state.loop_fingerprint();
    let prior = state.loop_fingerprints.iter().filter(|&&x| x == fp).count();
    state.loop_fingerprints.push_back(fp);
    if state.loop_fingerprints.len() > LOOP_FINGERPRINT_WINDOW {
        state.loop_fingerprints.pop_front();
    }
    if prior + 1 >= LOOP_DRAW_THRESHOLD {
        state.result = Some(GameResult::Draw);
    }
}
