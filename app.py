"""ContainNet: who should a hospital ward protect first?

Run locally:   streamlit run app.py
Deploy:        Streamlit Community Cloud, main file = app.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from containnet import communities as cm
from containnet.config import DEFAULTS, DISEASE_PRESETS, RESULTS_DIR, ROLE_NAMES
from containnet.data import load_graph
from containnet.simulation import Draws, arc_probability, patient_zero_potential, run_ic
from containnet.strategies import STRATEGY_INFO, build_context, compare_strategies, budget_curve, pick_targets
from ui import charts, components as comp_ui, theme

st.set_page_config(page_title="ContainNet", page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")
theme.inject()

PLAN_KEYS = ["bridge_score", "degree", "betweenness", "eigenvector", "community_degree", "cpm_bridge"]
NAV = ["Plan", "Replay", "Groups", "Evidence", "Dataset", "About"]

# ------------------------------------------------------------------ cached computation
@st.cache_resource(show_spinner=False)
def get_ctx(backbone_m: int, k: int):
    return build_context(load_graph(), backbone_m, k, louvain_runs=20)


@st.cache_data(show_spinner=False)
def get_pos(backbone_m: int):
    ctx = get_ctx(backbone_m, 3)
    return cm.community_layout(ctx.h, ctx.louvain)


@st.cache_data(show_spinner=False)
def get_comparison(backbone_m, k, beta, budget, trials, n_seeds, greedy):
    ctx = get_ctx(backbone_m, k)
    p = arc_probability(ctx.net, beta)
    return compare_strategies(ctx, p, budget, trials, n_seeds, DEFAULTS["rng_seed"], 15,
                              include_greedy=greedy, greedy_trials=250)

@st.cache_data(show_spinner=False)
def get_sizes(backbone_m, k, beta, budget, plan, trials, n_seeds):
    ctx = get_ctx(backbone_m, k)
    p = arc_probability(ctx.net, beta)
    draws = Draws.make(ctx.net, trials, DEFAULTS["rng_seed"])
    base = run_ic(ctx.net, p, draws, n_seeds=n_seeds)
    mine = run_ic(ctx.net, p, draws, blocked=pick_targets(ctx, plan, budget)[0], n_seeds=n_seeds)
    return base, mine

@st.cache_data(show_spinner=False)
def get_curve(backbone_m, k, beta, n_seeds):
    ctx = get_ctx(backbone_m, k)
    return budget_curve(ctx, arc_probability(ctx.net, beta), range(0, 16), trials=400, n_seeds=n_seeds, random_sets=8)


@st.cache_data(show_spinner=False)
def get_potential(backbone_m, k, beta):
    ctx = get_ctx(backbone_m, k)
    return patient_zero_potential(ctx.net, arc_probability(ctx.net, beta), trials=250)


@st.cache_data(show_spinner=False)
def get_method_table(backbone_m, k):
    g = load_graph()
    ctx = get_ctx(backbone_m, k)
    table, _ = cm.compare_methods(g, ctx.h, 10, k)
    return table

@st.cache_data(show_spinner=False)
def get_raw_tables():
    import zipfile

    from containnet.config import ZIP_PATH

    out = {}
    with zipfile.ZipFile(ZIP_PATH) as z:
        for name in z.namelist():
            low = name.lower()
            if low.endswith("edges.csv") or low.endswith("nodes.csv"):
                with z.open(name) as fh:
                    df = pd.read_csv(fh)
                df.columns = [str(c).lstrip("#").strip() for c in df.columns]
                out["edges" if "edges" in low else "nodes"] = df
    return out

def read_csv(name):
    p = RESULTS_DIR / name
    return pd.read_csv(p) if p.exists() else None


# ------------------------------------------------------------------ header
st.markdown('<h1 class="cn-title">ContainNet</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="cn-sub">A hospital ward has a handful of vaccine doses or isolation beds and an infection '
    "is about to start. Who should get them first? ContainNet finds the tight groups in a real ward, "
    "then simulates thousands of outbreaks to test each answer.</p>",
    unsafe_allow_html=True,
)

nav = st.radio("Section", NAV, horizontal=True, label_visibility="collapsed", key="nav")

# ------------------------------------------------------------------ scenario controls
with st.container(border=True):
    c1, c2, c3 = st.columns([1.1, 1.2, 1.5])
    with c1:
        disease = st.select_slider("How contagious is it?", options=list(DISEASE_PRESETS), value="Seasonal flu-like")
    with c2:
        budget = st.slider("People we can protect", 1, 20, DEFAULTS["budget"],
                           help="Vaccine doses or isolation beds. Protected people cannot be infected or pass infection on.")
    with c3:
        plan = st.selectbox("Who do we protect?", PLAN_KEYS, format_func=lambda k: STRATEGY_INFO[k][0],
                            help="Each plan is a different way to rank people. The first N on the list get protected.")
    with st.expander("Advanced settings"):
        a1, a2, a3, a4 = st.columns(4)
        backbone_m = a1.slider("Strongest ties kept per person", 3, 8, DEFAULTS["backbone_m"],
                               help="Used for overlapping groups. The raw ward is so dense that CPM merges everyone into one group.")
        k = a2.selectbox("Clique size k (CPM)", [3, 4, 5], index=0)
        trials = a3.select_slider("Simulated outbreaks per plan", [300, 600, 1000, 2000], value=1000)
        n_seeds = a4.selectbox("People who start the outbreak", [1, 2, 3], index=0)

beta = DISEASE_PRESETS[disease]
ctx = get_ctx(backbone_m, k)
n_people = ctx.net.n
st.caption(STRATEGY_INFO[plan][1])

with st.spinner("Simulating outbreaks..."):
    comp = get_comparison(backbone_m, k, beta, budget, trials, n_seeds, False)
row = comp[comp.strategy == plan].iloc[0]
base = comp[comp.strategy == "none"].iloc[0]
rnd = comp[comp.strategy == "random"].iloc[0]
targets = pick_targets(ctx, plan, budget)[0]
pos = get_pos(backbone_m)

# ================================================================== PLAN
if nav == "Plan":
    st.markdown(
        f'<div class="cn-verdict">Without a plan, an outbreak infects <span class="inf">{base.mean_infected:.0f}</span> '
        f'of {n_people} people on average. Protect {budget} with this plan and it infects '
        f'<span class="ok">{row.mean_infected:.0f}</span>, and only {row.takeoff_pct:.0f}% of outbreaks take off '
        f'(vs {base.takeoff_pct:.0f}%). Protecting {budget} at random gets it to {rnd.mean_infected:.0f}.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="cn-note">Part of any drop is automatic: protected people cannot be infected. '
        f'Random protection shows how much ({rnd.reduction_pct:.0f}%). What counts is the gap above it: '
        f'this plan prevents <b>{row.gain_over_random_pts:.0f} points more</b>. Among the {n_people - budget} people '
        f'left unprotected, {row.attack_rate_unprotected_pct:.0f}% get infected, against {base.attack_rate_pct:.0f}% with no plan.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        comp_ui.strip_block(f"<b>No plan</b>: {base.mean_infected:.0f} of {n_people} infected on average", n_people,
                            base.mean_infected, baseline=True)
        + comp_ui.strip_block(f"<b>With this plan</b>: {row.mean_infected:.0f} infected, {budget} protected, "
                              f"{row.reduction_pct:.0f}% fewer (±{row.reduction_ci:.0f})", n_people, row.mean_infected, budget)
        + comp_ui.LEGEND,
        unsafe_allow_html=True,
    )
    st.write("")
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("The ward")
        st.plotly_chart(charts.network(ctx, pos, charts.group_groups(ctx, targets), 560), width="stretch")
        st.caption("Each dot is a person, coloured by contact group (Louvain). Lines are each person's strongest "
                   "contacts. Ink diamonds are the people this plan protects.")
    with right:
        st.subheader("Protect these people first")
        pot = get_potential(backbone_m, k, beta).set_index("node")["outbreak_if_patient_zero"]
        tab = ctx.table.set_index("node", drop=False)
        with st.container(height=520, border=False):
            html = "".join(comp_ui.protect_card(i + 1, tab.loc[n], float(pot[n])) for i, n in enumerate(targets))
            st.markdown(html, unsafe_allow_html=True)
        out = tab.loc[targets][["node", "person_id", "role", "contacts", "strength", "louvain_group", "cpm_groups"]]
        st.download_button("Download this list (CSV)", out.to_csv(index=False), "protect_first.csv", "text/csv")

    st.subheader("What a typical outbreak looks like")
    b_sz, m_sz = get_sizes(backbone_m, k, beta, budget, plan, trials, n_seeds)
    st.plotly_chart(charts.size_distribution(b_sz, m_sz, n_people), width="stretch")
    st.caption("Outbreaks are all-or-nothing: many fizzle after a few people, the rest spread widely. "
               "A good plan mostly turns spreading outbreaks into fizzling ones, which a single average cannot show.")
    
    st.subheader("How this plan compares")
    st.plotly_chart(charts.leaderboard(comp, plan), width="stretch")
    st.caption(f"Every plan faces the same {trials:,} simulated outbreaks, so the gaps are real differences rather than "
               "luck. Whiskers show the 95% confidence interval of the improvement. 'Random people' is averaged over 15 random draws.")

# ================================================================== REPLAY
elif nav == "Replay":
    st.subheader("Watch one outbreak, with and without the plan")
    st.markdown('<p class="cn-note">Both sides use exactly the same chance events. The only difference is who is protected. '
                "Move the slider to step through transmission rounds.</p>", unsafe_allow_html=True)
    if "reroll" not in st.session_state:
        st.session_state.reroll = 0
    r1, r2, r3 = st.columns([2, 1.3, 1])
    unprotected = [n for n in ctx.net.nodes if n not in set(targets)]
    with r1:
        who = st.selectbox("Patient zero", ["A random unprotected person"] + unprotected,
                           format_func=lambda n: n if n.startswith("A ") else
                           f"Person {n} ({ROLE_NAMES.get(ctx.g.nodes[n].get('status', 'UNKNOWN'), '')})")
    with r2:
        take_off = st.toggle("Only show outbreaks that take off", value=True,
                             help="Many outbreaks fizzle after a few people. Switch off to see how often that happens.")
    with r3:
        st.write("")
        if st.button("Run another outbreak"):
            st.session_state.reroll += 1

    rng = np.random.default_rng(500 + st.session_state.reroll)
    pz = rng.choice(unprotected) if who.startswith("A ") else who
    p = arc_probability(ctx.net, beta)
    draws = Draws.make(ctx.net, 400, 1000 + st.session_state.reroll)
    sizes = run_ic(ctx.net, p, draws, seeds=[pz])
    pool = np.where(sizes >= 10)[0] if take_off and (sizes >= 10).any() else np.arange(len(sizes))
    i = int(pool[np.argmin(np.abs(sizes[pool] - np.median(sizes[pool])))])
    one = Draws(draws.u_arc[i:i + 1], draws.u_seed[i:i + 1])
    _, ra = run_ic(ctx.net, p, one, seeds=[pz], return_rounds=True)
    _, rb = run_ic(ctx.net, p, one, seeds=[pz], blocked=targets, return_rounds=True)
    ra, rb = ra[0], rb[0]
    last = int(max(ra.max(), rb.max()))
    step = st.slider("Transmission round", 0, max(last, 1), min(1, last))

    na = int(((ra >= 0) & (ra <= step)).sum())
    nb = int(((rb >= 0) & (rb <= step)).sum())
    ca, cb = st.columns(2, gap="large")
    with ca:
        st.markdown(f"#### No plan: {na} infected")
        st.plotly_chart(charts.network(ctx, pos, charts.outbreak_state(ctx, ra, step, [], [pz]), 470, False), width="stretch")
    with cb:
        st.markdown(f"#### With plan: {nb} infected")
        st.plotly_chart(charts.network(ctx, pos, charts.outbreak_state(ctx, rb, step, targets, [pz]), 470, False), width="stretch")
    st.plotly_chart(charts.cascade_curves(ra, rb, "No plan", "With plan"), width="stretch")
    final_a, final_b = int((ra >= 0).sum()), int((rb >= 0).sum())
    st.markdown(f'<p class="cn-note">In this run the outbreak reached <b>{final_a}</b> people without a plan and '
                f"<b>{final_b}</b> with it. One run is an anecdote; the Plan and Evidence sections average thousands.</p>",
                unsafe_allow_html=True)

# ================================================================== GROUPS
elif nav == "Groups":
    st.subheader("Who clusters with whom")
    mode = st.radio("Show", ["Louvain: everyone in exactly one group", "CPM: groups can overlap"], horizontal=True,
                    key="gmode")
    gl, gr = st.columns([3, 2], gap="large")
    with gl:
        if mode.startswith("Louvain"):
            st.plotly_chart(charts.network(ctx, pos, charts.group_groups(ctx), 560), width="stretch")
            st.caption(f"{len(ctx.louvain)} groups, modularity {ctx.louvain_q:.2f}. Louvain is fast and scales to huge networks, "
                       "but it cannot show someone who belongs to two groups.")
        else:
            st.plotly_chart(charts.network(ctx, pos, charts.cpm_groups(ctx), 560), width="stretch")
            st.caption(f"Clique Percolation (k={k}) on each person's {backbone_m} strongest ties: {len(ctx.cpm)} groups, "
                       f"{len(ctx.overlap)} people in more than one (amber, numbered).")
    with gr:
        st.markdown("##### Who is in each group")
        st.plotly_chart(charts.role_stack(ctx), width="stretch")
        st.markdown("##### Busiest person in each group")
        top = ctx.table.sort_values("strength", ascending=False).groupby("louvain_group").head(1).sort_values("louvain_group")
        st.dataframe(
            pd.DataFrame({"Group": top.louvain_group, "Person": top.node, "Role": top.role.map(ROLE_NAMES),
                          "Contacts": top.contacts, "Bridge score": top.bridge_score.round(2)}),
            hide_index=True, width="stretch")

    if ctx.overlap:
        st.markdown("##### People who sit between groups (CPM)")
        ov = ctx.table[ctx.table.cpm_groups > 1]
        st.dataframe(
            pd.DataFrame({"Person": ov.node, "Role": ov.role.map(ROLE_NAMES), "Overlapping groups": ov.cpm_groups,
                          "Contacts": ov.contacts, "Betweenness": ov.betweenness.round(3), "Degree rank": ov.degree_rank})
            .sort_values("Overlapping groups", ascending=False),
            hide_index=True, width="stretch")
    else:
        st.info("CPM found nobody in two groups with these settings. Try a different k or keep fewer strongest ties.")

    st.markdown("##### Why CPM needs the backbone")
    sweep = read_csv("cpm_sweep.csv")
    if sweep is not None:
        s1, s2 = st.columns(2)
        s1.plotly_chart(charts.sweep_heatmap(sweep, "communities", "Groups found (1 means everyone merged)"), width="stretch")
        s2.plotly_chart(charts.sweep_heatmap(sweep, "people_in_2plus", "People in 2+ groups"), width="stretch")
    st.markdown('<p class="cn-note">In this ward 41% of all possible pairs were in contact at some point, so on the full graph '
                "CPM chains every triangle together into one 75-person blob and finds nobody in between. Keeping only each "
                "person's strongest ties removes the brief incidental contacts and lets real groups appear.</p>",
                unsafe_allow_html=True)

# ================================================================== EVIDENCE
elif nav == "Evidence":
    st.subheader("Does it hold up?")
    st.markdown("##### Plans head to head, including a simulation-optimised benchmark")
    include_greedy = st.toggle("Add the benchmark (greedy search over simulations, about 10 seconds)", value=False)
    if include_greedy:
        with st.spinner("Searching for the best possible set of people..."):
            comp_e = get_comparison(backbone_m, k, beta, budget, trials, n_seeds, True)
    else:
        comp_e = comp
        show = comp_e[["label", "protected", "mean_infected", "ci95", "reduction_pct", "reduction_ci", "gain_over_random_pts", "takeoff_pct"]].copy()
    show.columns = ["Plan", "Protected", "Avg infected", "± 95% CI", "Fewer infected (%)", "± CI (pts)", "Gain over random (pts)", "Outbreaks that take off (%)"]
    st.dataframe(show.round(1), hide_index=True, width="stretch")
    st.download_button("Download table (CSV)", show.round(3).to_csv(index=False), "strategy_comparison.csv", "text/csv")
    if include_greedy:
        g_row = comp_e[comp_e.strategy == "greedy"].iloc[0]
        st.markdown(f'<p class="cn-note">The benchmark protects {g_row.reduction_pct:.0f}% fewer infections. Plans within its confidence '
                    "interval are as good as anything this budget can buy.</p>", unsafe_allow_html=True)

    st.markdown("##### More doses, fewer infections")
    with st.spinner("Computing the curve..."):
        curve = get_curve(backbone_m, k, beta, n_seeds)
    st.plotly_chart(charts.budget_curve(curve, plan), width="stretch")
    st.caption("Average outbreak size as the number of protected people goes from 0 to 15. The selected plan is drawn thick.")

    e1, e2 = st.columns(2, gap="large")
    with e1:
        st.markdown("##### Which score predicts real spreading power?")
        corr = read_csv("centrality_vs_simulated_spread.csv")
        if corr is not None:
            st.plotly_chart(charts.correlation_bars(corr), width="stretch")
            st.caption("Each person was made patient zero in turn. Total contact time tracks the simulation almost perfectly; "
                       "group-mixing on its own does not.")
    with e2:
        st.markdown("##### Most dangerous patient zero")
        pz_df = get_potential(backbone_m, k, beta).merge(ctx.table[["node", "role"]], on="node")
        st.plotly_chart(charts.potential_bars(pz_df, 12), width="stretch")
        st.caption("Colour shows role. Outbreak size is averaged over 250 runs per person.")

    st.markdown("##### Does the ranking change with the disease?")
    sens = read_csv("disease_sensitivity.csv")
    if sens is not None:
        st.plotly_chart(charts.disease_sensitivity(sens), width="stretch")
        st.caption("Pre-computed with 8 people protected (see results/disease_sensitivity.csv). Faster-spreading diseases "
                   "blunt every plan, but the order stays similar.")

    st.markdown("##### Community methods side by side")
    with st.spinner("Comparing Louvain, Girvan-Newman and CPM..."):
        mt = get_method_table(backbone_m, k)
    st.dataframe(mt.rename(columns={
        "method": "Method", "communities": "Groups", "largest": "Largest", "avg_size": "Avg size", "people_covered": "People covered",
        "people_in_2plus": "In 2+ groups", "modularity": "Modularity", "within_group_contact": "Contact kept inside groups",
        "nmi_vs_roles": "Match with job roles (NMI)", "runtime_s": "Seconds"}), hide_index=True, width="stretch")

    st.markdown("##### Does it scale?")
    sc = read_csv("scalability.csv")
    if sc is not None:
        st.plotly_chart(charts.scalability(sc), width="stretch")
        st.caption("Synthetic community networks up to 5,000 people. The ward in this app has 75, so everything here is instant.")

    st.markdown("##### What to be careful about")
    st.markdown(
        "- One ward, 75 people, four days. Trust the *order* of the plans more than the exact percentages.\n"
        "- Contact is summed over four days, so *when* people met is ignored.\n"
        "- Protection is perfect and instant here. Real vaccines take time and are imperfect.\n"
        "- Overlapping membership alone is a weak signal. People in several groups are often patients with few contacts overall; "
        "the bridge score works because it also weighs how much contact a person has."
    )

    
elif nav == "Dataset":
    raw = get_raw_tables()
    events = raw["edges"]
    st.subheader("The dataset")
    st.markdown(
        f"**SocioPatterns Hospital Ward contact network** (Vanhems et al., PLoS ONE 2013), recorded in a hospital in Lyon, "
        f"France, in December 2010. {n_people} people (46 health-care workers and 29 patients) wore badges that logged "
        f"face-to-face proximity for about four days. That gave **{len(events):,} contacts**, each a 20-second interval "
        f"between two people. We add up each pair's contacts into one network of **{ctx.g.number_of_edges():,} linked pairs**, "
        "where a stronger link means more time together. The data records who met whom, not who got infected."
    )
    view = st.radio("Table", [f"People ({n_people})", f"Contact pairs ({ctx.g.number_of_edges():,})",
                              f"Raw contact events ({len(events):,})"], horizontal=True, key="dview")
    if view.startswith("People"):
        t = ctx.table.copy()
        t["node"] = t["node"].astype(int)
        t = t.sort_values("node")
        df = pd.DataFrame({"Person": t.node, "Badge id": t.person_id, "Role": t.role.map(ROLE_NAMES),
                           "Contacts": t.contacts, "Contact intervals": t.strength})
        fname = "people.csv"
    elif view.startswith("Contact pairs"):
        df = pd.DataFrame([{"Person A": u, "Person B": v, "Contact intervals": d["weight"], "Seconds together": d["weight"] * 20}
                           for u, v, d in ctx.g.edges(data=True)]).sort_values("Contact intervals", ascending=False)
        fname = "contact_pairs.csv"
    else:
        df = events.rename(columns={"source": "Person A", "target": "Person B", "time": "Time (seconds since start)"})
        fname = "raw_contact_events.csv"
    st.dataframe(df, hide_index=True, width="stretch", height=520)
    st.download_button("Download this table (CSV)", df.to_csv(index=False), fname, "text/csv")
    st.caption("Source: networks.skewed.de/net/sp_hospital. One contact interval is 20 seconds, so 'Contact intervals' of 3 means one minute together.")

# ================================================================== ABOUT
else:
    st.subheader("How it works")
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown(
            "**1. Real data.** The SocioPatterns hospital ward study (Lyon, 2010) gave 46 health-care workers and "
            "29 patients wearable badges for four days. About 32,000 face-to-face contacts, each 20 seconds long, "
            "are summed into one network. More shared time means a stronger link.\n\n"
            "**2. Find the groups.** Louvain splits the ward into tight clusters. Girvan-Newman does the same more slowly "
            "as a cross-check. Clique Percolation finds groups that can overlap, but only after the network is thinned "
            "to each person's strongest ties.\n\n"
            "**3. Score everyone.** Contacts, total contact time, betweenness, eigenvector centrality and a bridge score "
            "(how much contact someone has, and how widely it is spread across groups)."
        )
    with b:
        st.markdown(
            "**4. Simulate outbreaks.** Independent Cascade: every contact gets one chance to pass the infection, with a "
            "probability that grows with contact time. We run thousands of outbreaks at once with NumPy and reuse the same "
            "random numbers for every plan, so plans are compared fairly.\n\n"
            "**5. Test the plans.** Protect the top N people from each ranking, re-run the outbreaks, and measure how "
            "many fewer people are infected. Patient zero is always someone who is not protected.\n\n"
            "**6. Check against a ceiling.** A greedy search picks, one by one, whoever helps most in simulation. "
            "It marks roughly the best any plan can do."
        )
    st.markdown("##### Data and credits")
    st.markdown(
        "Vanhems et al., *Estimating potential infection transmission routes in hospital wards using wearable proximity sensors*, "
        "PLoS ONE 8(9): e73970 (2013). Dataset via the Netzschleuder repository. Built for a social-network analysis "
        "course project: Louvain, Girvan-Newman, centrality and Independent Cascade from the syllabus, "
        "Clique Percolation and the intervention comparison beyond it.")
