// Verbatim excerpt from Arcana at 4265da606717b58b983b77d1c3621acf979f223f.
// arcana-cards/src/s2x2/liliana_the_last_hope.rs, lines 182-215.
// https://github.com/levineuwirth/arcana/blob/4265da606717b58b983b77d1c3621acf979f223f/arcana-cards/src/s2x2/liliana_the_last_hope.rs#L182-L215
// Excerpt only; imports and surrounding context are omitted.
// MIT license: see ARCANA-LICENSE.txt.

/// Emblem end-step trigger: create (2 + Zombies you control) 2/2 black Zombies.
fn emblem_make_zombies(
    state: &GameState,
    trig: &PendingTrigger,
    reg: &CardRegistry,
) -> Vec<Effect> {
    let zombie = reg.interner().lookup("Zombie").expect("Zombie interned");
    let filter = script::subtype_filter(reg, "Zombie")
        .controlled_by(ControllerConstraint::You);
    let zombies = script::count_matching(state, &filter, trig.controller);
    let x = 2 + zombies;

    let mut st = SubtypeSet::default();
    st.0.insert(zombie);
    let token = TokenDefinition {
        name: zombie,
        colors: ColorSet::black(),
        types: TypeLine::CREATURE.into(),
        subtypes: st,
        power: Some(PtValue::Fixed(2)),
        toughness: Some(PtValue::Fixed(2)),
        keywords: vec![],
        abilities: vec![],
    };

    let mut effects = Vec::new();
    for _ in 0..x {
        effects.push(Effect::CreateToken {
            controller: trig.controller,
            token: token.clone(),
        });
    }
    effects
}
