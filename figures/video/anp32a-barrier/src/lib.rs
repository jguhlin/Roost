//! Educational explainer (≈2.8 min): ANP32A and the species barrier.
//!
//! Lecture style per MEDIA_PLAN editorial review: six numbered sections,
//! lines appear ~4 s apart and stay readable, calm fades only, section
//! progress dots. Static svgr! structure with computed opacities.
//!
//! For `#/research/how-does-anp32a-determine-the-species-barrier-between-birds-and`.
use fframes::{
    AudioMap, AudioTimestamp::*, AudioTrack, Color, Duration, FFramesContext,
    Frame, Svgr, Video, include_media_dir,
};

include_media_dir!(pub struct Anp32aMedia, "media");

pub const WIDTH: usize = 1920;
pub const HEIGHT: usize = 1080;
const UNIT: f32 = HEIGHT as f32 / 1080.0;

const FONT: &str = "DM Sans";
const W: u16 = 500;
const INK: &str = "#0f172a";
const MUTED: &str = "#475569";
const FAINT: &str = "#94a3b8";
const BLUE: &str = "#1d4ed8";
const BLUE_BG: &str = "#eff6ff";
const GREEN: &str = "#166534";
const GREEN_BG: &str = "#f0fdf4";
const AMBER: &str = "#92400e";
const AMBER_BG: &str = "#fffbeb";

/// Section timings: (start, next_start, label, title, accent, accent_bg)
const SEC: &[(f32, f32, &str, &str, &str, &str)] = &[
    (0.5, 27.0, "1 / 6", "The question", BLUE, BLUE_BG),
    (27.0, 54.0, "2 / 6", "The protein: ANP32A", BLUE, BLUE_BG),
    (54.0, 82.0, "3 / 6", "The knockout experiment", GREEN, GREEN_BG),
    (82.0, 110.0, "4 / 6", "Species matching", BLUE, BLUE_BG),
    (110.0, 140.0, "5 / 6", "Adaptation breaks the barrier", AMBER, AMBER_BG),
    (140.0, 168.0, "6 / 6", "What remains open", MUTED, "#f1f5f9"),
];

pub struct Anp32aVideo<'a> {
    pub media: &'a Anp32aMedia,
}

impl std::fmt::Debug for Anp32aVideo<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Anp32aVideo").finish()
    }
}

impl Video for Anp32aVideo<'_> {
    const FPS: usize = 30;
    const WIDTH: usize = WIDTH;
    const HEIGHT: usize = HEIGHT;
    const BACKGROUND_COLOR: Color = Color::WHITE;

    fn duration(&self) -> Duration<'_> {
        Duration::Seconds(168.0)
    }

    fn audio(&self) -> AudioMap<'_> {
        AudioMap::from([
            AudioTrack::new("ambient-pad.wav", Second(0.)..Eof)
                .gain_db(-20.).fade_in(2.).fade_out(2.),
        ])
    }

    fn render_frame<'a>(&'a self, mut frame: Frame, ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let _ = &ctx;
        let t = frame.seconds() as f32;
        let f = |from: f32, dur: f32| if t < from { 0.0 } else { ((t - from) / dur).min(1.0) };
        // section visibility: fade in after start, fade out before next
        let vis = |i: usize| {
            let (s, n, ..) = SEC[i];
            let mut v = f(s, 0.7);
            if n - t < 0.7 { v *= ((n - t) / 0.7).max(0.0); }
            v
        };
        // line opacity: line j of section i
        let line = |i: usize, j: usize| f(SEC[i].0 + 0.8 + j as f32 * 4.2, 0.7);
        // progress dot fill
        let dot = |i: usize| if t >= SEC[i].0 { SEC[i].4 } else { "#cbd5e1" };

        let cx = WIDTH as f32 / 2.0;
        let x0 = 150.0 * UNIT;

        fframes::svgr!(
            <svg xmlns="http://www.w3.org/2000/svg" viewBox={format!("0 0 {WIDTH} {HEIGHT}")} width={WIDTH} height={HEIGHT}>
                <rect width={WIDTH} height={HEIGHT} fill="#f8fafc" />

                <g opacity={vis(0)}>
                    <rect x={x0} y={148. * UNIT} width={980. * UNIT} height={92. * UNIT} rx={14. * UNIT} fill={SEC[0].5} />
                    <text x={x0 + 30. * UNIT} y={208. * UNIT} font-family={FONT} font-size={38. * UNIT} font-weight={700} fill={SEC[0].4}>{format!("{}  ·  {}", SEC[0].2, SEC[0].3)}</text>
                    <text x={x0} y={330. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(0, 0)}>"Avian influenza H5N1 circulates constantly in wild birds."</text>
                    <text x={x0} y={438. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(0, 1)}>"When it spills into mammals — cattle, cats, humans — infection is often severe,"</text>
                    <text x={x0} y={486. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(0, 1)}>"but rarely sustains transmission."</text>
                    <text x={x0} y={594. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(0, 2)}>"The virus carries its own polymerase — the enzyme complex that copies its genome."</text>
                    <text x={x0} y={702. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(0, 3)}>"But that polymerase cannot work alone: it needs a helper protein from the cell it infects."</text>
                    <text x={x0} y={810. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(0, 4)}>"So the question becomes: which helper protein — and why does species matter?"</text>
                </g>

                <g opacity={vis(1)}>
                    <rect x={x0} y={148. * UNIT} width={820. * UNIT} height={92. * UNIT} rx={14. * UNIT} fill={SEC[1].5} />
                    <text x={x0 + 30. * UNIT} y={208. * UNIT} font-family={FONT} font-size={38. * UNIT} font-weight={700} fill={SEC[1].4}>{format!("{}  ·  {}", SEC[1].2, SEC[1].3)}</text>
                    <text x={x0} y={330. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(1, 0)}>"That helper is ANP32A — a host protein in the nucleus of every cell."</text>
                    <text x={x0} y={438. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(1, 1)}>"Avian ANP32A carries a 33-amino-acid insertion that mammalian ANP32A lacks."</text>
                    <text x={x0} y={546. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(1, 2)}>"The avian viral polymerase (with PB2 residue 627E) is built to grip that insertion."</text>
                    <text x={x0} y={654. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(1, 3)}>"No insertion, no support: the mammalian protein is a poor match for the avian enzyme."</text>
                    <text x={x0} y={762. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(1, 4)}>"One insertion in one host protein — that is the species barrier in miniature."</text>
                </g>

                <g opacity={vis(2)}>
                    <rect x={x0} y={148. * UNIT} width={900. * UNIT} height={92. * UNIT} rx={14. * UNIT} fill={SEC[2].5} />
                    <text x={x0 + 30. * UNIT} y={208. * UNIT} font-family={FONT} font-size={38. * UNIT} font-weight={700} fill={SEC[2].4}>{format!("{}  ·  {}", SEC[2].2, SEC[2].3)}</text>
                    <text x={x0} y={330. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(2, 0)}>"Chicken cells engineered without ANP32A are essentially refractory:"</text>
                    <text x={x0} y={378. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(2, 0)}>"no infectious H5N1 or H7N9 detected. [pb2_cattle_adaptation2026]"</text>
                    <text x={x0} y={486. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(2, 1)}>"Add ANP32A back alone — replication is restored. A is necessary and sufficient."</text>
                    <text x={x0} y={594. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(2, 2)}>"ANP32B does not rescue it: chicken ANP32B is a non-functional paralog."</text>
                    <text x={x0} y={702. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(2, 3)}>"ANP32E does not compensate either; a triple A/B/E knockout stays refractory."</text>
                    <text x={x0} y={810. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(2, 4)}>"In birds, productive infection runs on ANP32A — or nothing."</text>
                </g>

                <g opacity={vis(3)}>
                    <rect x={x0} y={148. * UNIT} width={780. * UNIT} height={92. * UNIT} rx={14. * UNIT} fill={SEC[3].5} />
                    <text x={x0 + 30. * UNIT} y={208. * UNIT} font-family={FONT} font-size={38. * UNIT} font-weight={700} fill={SEC[3].4}>{format!("{}  ·  {}", SEC[3].2, SEC[3].3)}</text>
                    <text x={x0} y={330. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 0)}>"Does any species' ANP32A work? No — matching matters."</text>
                    <text x={x0} y={438. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 1)}>"In human knockout cells (eHAP), complemented with ANP32 proteins"</text>
                    <text x={x0} y={486. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 1)}>"from different species…"</text>
                    <text x={x0} y={594. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 2)}>"…only chicken ANP32A robustly supported the avian polymerase —"</text>
                    <text x={x0} y={642. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 2)}>"and the cattle/Texas precursor. [pb2_cattle_adaptation2026]"</text>
                    <text x={x0} y={750. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 3)}>"Species-matched ANP32A is required for robust activity."</text>
                    <text x={x0} y={858. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(3, 4)}>"The barrier is not just presence or absence — it is sequence compatibility."</text>
                </g>

                <g opacity={vis(4)}>
                    <rect x={x0} y={148. * UNIT} width={1040. * UNIT} height={92. * UNIT} rx={14. * UNIT} fill={SEC[4].5} />
                    <text x={x0 + 30. * UNIT} y={208. * UNIT} font-family={FONT} font-size={38. * UNIT} font-weight={700} fill={SEC[4].4}>{format!("{}  ·  {}", SEC[4].2, SEC[4].3)}</text>
                    <text x={x0} y={330. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 0)}>"Mammalian-adapting mutations let the polymerase work without the avian insertion."</text>
                    <text x={x0} y={438. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 1)}>"PB2 E627K is the classic route: it lifts human-cell polymerase activity"</text>
                    <text x={x0} y={486. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 1)}>"far above the avian baseline. [matthew2025]"</text>
                    <text x={x0} y={594. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 2)}>"Cattle found another: B3.13 fixes PB2 M631L (+ PA K497R) — its avian-like"</text>
                    <text x={x0} y={642. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 2)}>"ancestor is ~10× less active. [pb2_cattle_adaptation2026]"</text>
                    <text x={x0} y={750. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 3)}>"Two different mutations, one destination: a polymerase tuned to mammalian ANP32."</text>
                    <text x={x0} y={858. * UNIT} font-family={FONT} font-size={30. * UNIT} font-weight={W} fill={INK} opacity={line(4, 4)}>"This is convergent adaptation at the polymerase–ANP32 interface."</text>
                </g>

                <g opacity={vis(5)}>
                    <rect x={x0} y={148. * UNIT} width={820. * UNIT} height={92. * UNIT} rx={14. * UNIT} fill={SEC[5].5} />
                    <text x={x0 + 30. * UNIT} y={208. * UNIT} font-family={FONT} font-size={38. * UNIT} font-weight={700} fill={SEC[5].4}>{format!("{}  ·  {}", SEC[5].2, SEC[5].3)}</text>
                    <text x={x0} y={330. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(5, 0)}>"Gene-edited ANP32A (N129I–D130N) slows the virus but does not stop it:"</text>
                    <text x={x0} y={378. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(5, 0)}>"compensatory PA-349K + PB2-M631L emerge at high dose."</text>
                    <text x={x0} y={486. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(5, 1)}>"So editing host resistance is leaky under challenge — a resilience question."</text>
                    <text x={x0} y={594. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(5, 2)}>"Whether E627K-like and M631L-like routes are predictably convergent is unresolved."</text>
                    <text x={x0} y={702. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(5, 3)}>"Sources: pb2_cattle_adaptation2026 · matthew2025 · briefing corpus."</text>
                    <text x={x0} y={810. * UNIT} font-family={FONT} font-size={29. * UNIT} font-weight={W} fill={INK} opacity={line(5, 4)}>"Full briefing, figure and citations: linked below."</text>
                </g>

                <circle cx={cx - 115. * UNIT} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={dot(0)} />
                <circle cx={cx - 69. * UNIT} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={dot(1)} />
                <circle cx={cx - 23. * UNIT} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={dot(2)} />
                <circle cx={cx + 23. * UNIT} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={dot(3)} />
                <circle cx={cx + 69. * UNIT} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={dot(4)} />
                <circle cx={cx + 115. * UNIT} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={dot(5)} />

                <text x={52. * UNIT} y={HEIGHT as f32 - 22. * UNIT} font-family={FONT} font-size={19. * UNIT} font-weight={W} fill={FAINT}>
                    "Roost · educational explainer · briefing: how-does-anp32a-determine-the-species-barrier-between-birds-and"
                </text>
            </svg>
        )
    }
}
