// Verbatim excerpt from Arcana at 4265da606717b58b983b77d1c3621acf979f223f.
// arcana-core/src/engine.rs, lines 3000-3033.
// https://github.com/levineuwirth/arcana/blob/4265da606717b58b983b77d1c3621acf979f223f/arcana-core/src/engine.rs#L3000-L3033
// Excerpt only; imports and surrounding context are omitted.
// MIT license: see ARCANA-LICENSE.txt.

        // 3f. Pass 3.6 long tail. Evolve: a creature its controller
        //     controls entered with greater power OR toughness.
        if let crate::events::GameEvent::EntersBattlefield { object_id, .. } = event {
            use crate::effects::KeywordAbility as KA;
            if let Some(entrant) = state.objects.get(*object_id) {
                if entrant.is_creature() && entrant.zone.is_battlefield() {
                    let ctrl = entrant.controller;
                    let ep = state.computed_power(*object_id).unwrap_or(0);
                    let et = state.computed_toughness(*object_id).unwrap_or(0);
                    let evolvers: Vec<ObjectId> = state.objects
                        .objects_in_zone(Zone::Battlefield)
                        .filter(|o| o.controller == ctrl && o.id != *object_id)
                        .map(|o| o.id)
                        .filter(|id| state.effective_keywords(*id)
                            .iter().any(|k| matches!(k, KA::Evolve)))
                        .filter(|id| {
                            ep > state.computed_power(*id).unwrap_or(i32::MAX)
                            || et > state.computed_toughness(*id).unwrap_or(i32::MAX)
                        })
                        .collect();
                    for src in evolvers {
                        let c = state.objects.get(src)
                            .map(|o| o.controller).unwrap_or(0);
                        pending.push(crate::triggers::PendingTrigger {
                            source: src, trigger_id: EVOLVE_TRIGGER_ID,
                            controller: c, trigger_event: event.clone(),
                            targets: crate::targets::TargetSelection::new(),
                            effect_override: None,
                            affected: None,
                        });
                    }
                }
            }
        }
