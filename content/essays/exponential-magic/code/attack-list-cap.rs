// Verbatim excerpt from Arcana at 4265da606717b58b983b77d1c3621acf979f223f.
// arcana-core/src/legal_actions.rs, lines 1019-1043.
// https://github.com/levineuwirth/arcana/blob/4265da606717b58b983b77d1c3621acf979f223f/arcana-core/src/legal_actions.rs#L1019-L1043
// Excerpt only; imports and surrounding context are omitted.
// MIT license: see ARCANA-LICENSE.txt.

        // DEGRADE (combinatorial blowup beyond the cap): emit a bounded but
        // strategically meaningful subset — every singleton (attacker ×
        // defender) plus the "all able attackers vs one defender" alpha-strike
        // for each distinct defender. Mid-size subsets are omitted; declining
        // and focused/all-in attacks stay available.
        for (atk, defs) in &slots {
            for &def in defs {
                if out.len() >= MAX_COMBAT_ENUM { return out; }
                let decl = vec![AttackerDeclaration { attacker: *atk, defending: def }];
                if tax_ok(&decl) { out.push(Action::DeclareAttackers { attackers: decl }); }
            }
        }
        let distinct: Vec<DefendingEntity> = opponents.iter().map(|&o| DefendingEntity::Player(o))
            .chain(extra_defenders.iter().copied()).collect();
        for def in distinct {
            if out.len() >= MAX_COMBAT_ENUM { return out; }
            let decl: Vec<AttackerDeclaration> = slots.iter()
                .filter(|(_, defs)| defs.contains(&def))
                .map(|(atk, _)| AttackerDeclaration { attacker: *atk, defending: def })
                .collect();
            if !decl.is_empty() && tax_ok(&decl) {
                out.push(Action::DeclareAttackers { attackers: decl });
            }
        }
    }
