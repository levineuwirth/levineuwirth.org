// Verbatim excerpt from Arcana at 4265da606717b58b983b77d1c3621acf979f223f.
// arcana-core/src/layers.rs, lines 1931-1940.
// https://github.com/levineuwirth/arcana/blob/4265da606717b58b983b77d1c3621acf979f223f/arcana-core/src/layers.rs#L1931-L1940
// Excerpt only; imports and surrounding context are omitted.
// MIT license: see ARCANA-LICENSE.txt.

            if layer == Layer::L7dPTCounters {
                // Inline: fold the object's own +1/+1 and -1/-1
                // counters. Each pair contributes (+1, +1) / (-1, -1)
                // to P and T respectively.
                let plus = obj.count_counters(CounterKind::PlusOnePlusOne) as i32;
                let minus = obj.count_counters(CounterKind::MinusOneMinusOne) as i32;
                let delta = plus - minus;
                add_to_pt(&mut chars, delta, delta);
                continue;
            }
