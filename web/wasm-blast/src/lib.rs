//! Static BLASTP kernel for the Roost web app (FUTURE_TODO #3).
//!
//! Smith-Waterman local alignment with BLOSUM62 and affine gaps
//! (open 11 / extend 1 — NCBI blastp defaults), full traceback.
//! Significance via Karlin-Altschul parameters for that scoring
//! setup (lambda = 0.267, K = 0.041). The database is set once
//! from JS (protein sequences), then queries run against it and
//! return ranked hits with alignment strings.
use wasm_bindgen::prelude::*;

const AA: &[u8] = b"ARNDCQEGHILKMFPSTWYVBZX*";
const BLOSUM62: [[i8; 24]; 24] = [
    [ 4,-1,-2,-2, 0,-1,-1, 0,-2,-1,-1,-1,-1,-2,-1, 1, 0,-3,-2, 0,-2,-1, 0,-4],
    [-1, 5, 0,-2,-3, 1, 0,-2, 0,-3,-2, 2,-1,-3,-2,-1,-1,-3,-2,-3,-1, 0,-1,-4],
    [-2, 0, 6, 1,-3, 0, 2,-2,-1,-3,-1, 0,-1,-2,-1,-1,-1,-2,-2,-3,-1, 0,-1,-4],
    [-2,-2, 1, 6,-3, 0, 3,-2,-2,-3,-4, 0,-3,-3,-2,-1,-1,-4,-3,-3,-1, 0,-1,-4],
    [ 0,-3,-3,-3, 9,-3,-4,-3,-3,-1,-1,-3,-2,-3,-2,-2,-1,-2,-2,-1,-3,-3,-2,-4],
    [-1, 1, 0, 0,-3, 5, 2,-2, 0,-3,-2, 1, 0,-3,-1, 0,-1,-2,-1,-2, 0, 3,-1,-4],
    [-1, 0, 2, 3,-4, 2, 5,-2, 0,-3,-3, 1,-2,-3,-1, 0,-1,-3,-2,-2, 1, 4,-1,-4],
    [ 0,-2,-2,-2,-3,-2,-2, 6,-2,-4,-4,-2,-3,-3,-2, 0,-2,-2,-3,-3,-1,-2,-1,-4],
    [-2, 0,-1,-2,-3, 0, 0,-2, 8,-3,-3,-1,-2,-1,-2,-1,-2,-2, 2,-3, 0, 0,-1,-4],
    [-1,-3,-3,-3,-1,-3,-3,-4,-3, 4, 2,-3, 1, 0,-3,-2,-1,-3,-1, 3,-3,-3,-1,-4],
    [-1,-2,-3,-4,-1,-2,-3,-4,-3, 2, 4,-2, 2, 0,-3,-2,-1,-2,-1, 1,-4,-3,-1,-4],
    [-1, 2, 0, 0,-2, 1, 1,-2,-1,-3,-2, 5,-1,-3,-1, 0,-1,-3,-2,-2, 0, 3,-1,-4],
    [-1,-1,-1,-3,-2, 0,-2,-3,-2, 1, 2,-1, 5, 0,-2,-1,-1,-1,-1, 1,-3,-1,-1,-4],
    [-2,-3,-3,-3,-3,-3,-3,-3,-1, 0, 0,-3, 0, 6,-4,-2,-2, 1, 3,-1,-3,-3,-1,-4],
    [-1,-2,-2,-2,-2,-2,-1,-2,-2,-3,-3,-1,-2,-4, 7,-1,-1,-4,-3,-2,-2,-1,-2,-4],
    [ 1,-1,-1,-1,-2, 0, 0,-2,-1,-3,-2, 0,-3,-2,-1, 4, 1,-3,-2,-2, 0, 0, 0,-4],
    [ 0,-1,-1,-1,-1,-1,-1,-2,-2,-1,-1,-1,-1,-2,-1, 1, 5,-2,-2, 0,-1,-1, 0,-4],
    [-3,-3,-4,-4,-2,-2,-3,-2,-2,-3,-2,-3,-1, 1,-4,-3,-2,11, 2,-3,-4,-3,-2,-4],
    [-2,-2,-2,-3,-2,-1,-2,-3, 2,-1,-1,-2,-1, 3,-3,-2,-2, 2, 7,-1,-2,-2,-1,-4],
    [ 0,-3,-3,-3,-1,-2,-2,-3,-3, 3, 1,-2, 1,-1,-2,-2, 0,-3,-1, 4,-3,-2,-1,-4],
    [-2,-1, 3, 0,-3, 0, 1,-1, 0,-3,-4, 0,-3,-3,-2, 0,-1,-4,-2,-3, 4, 1,-1,-4],
    [-1, 0, 0,-2, 0, 3, 4,-2, 0,-3,-3, 1,-1,-3,-1, 0,-1,-3,-2,-2, 1, 4,-1,-4],
    [ 0,-1,-1,-1,-2,-1,-1,-1,-1,-1,-1,-1,-1,-1,-2, 0, 0,-2,-1,-1,-1,-1,-1,-4],
    [-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4, 1],
];
// BLOSUM62 gap 11/1 Karlin-Altschul parameters
const LAMBDA: f64 = 0.267;
const K_PARAM: f64 = 0.041;

const fn build_lut() -> [u8; 256] {
    let mut lut = [22u8; 256];
    let codes = *b"ARNDCQEGHILKMFPSTWYVBZX*";
    let mut i = 0;
    while i < codes.len() {
        lut[codes[i] as usize] = i as u8;
        i += 1;
    }
    lut
}
static LUT: [u8; 256] = build_lut();

#[inline(always)]
fn aa_idx(c: u8) -> usize {
    LUT[c as usize] as usize
}

#[derive(Clone)]
struct Target {
    gene: String,
    species: String,
    desc: String,
    seq: Vec<u8>,
}

struct Alignment {
    score: i32,
    q_start: usize,
    q_end: usize,
    t_start: usize,
    t_end: usize,
    q_aln: String,
    midline: String,
    t_aln: String,
    identities: usize,
    positives: usize,
    gaps: usize,
}

/// affine Smith-Waterman with full traceback
fn sw(query: &[u8], target: &[u8], go: i32, ge: i32) -> Alignment {
    let n = query.len();
    let m = target.len();
    // rows: E (gap in query), F (gap in target), H (best), pointer
    // pointer: 0 = diagonal, 1 = up (gap in target / F), 2 = left (gap in query / E)
    let mut h_prev = vec![0i32; m + 1];
    let mut h_cur = vec![0i32; m + 1];
    let mut e_row = vec![0i32; m + 1]; // gap in query (left)
    let mut ptr = vec![vec![0u8; m + 1]; n + 1];
    let mut best = 0i32;
    let mut best_i = 0usize;
    let mut best_j = 0usize;
    let mut f_col;
    for i in 1..=n {
        f_col = 0;
        h_cur[0] = 0;
        let qi = aa_idx(query[i - 1]);
        for j in 1..=m {
            // E: gap in query (residue of target aligned to gap)
            let e_open = h_cur[j - 1] - go;
            let e_ext = if e_row[j] == 0 { i32::MIN / 2 } else { e_row[j] - ge };
            let e = e_open.max(e_ext);
            // F: gap in target
            let f_open = h_prev[j] - go;
            let f_ext = if f_col == 0 { i32::MIN / 2 } else { f_col - ge };
            let f = f_open.max(f_ext);
            let diag = h_prev[j - 1] + BLOSUM62[qi][aa_idx(target[j - 1])] as i32;
            let mut val = diag;
            let mut p = 0u8;
            if e > val { val = e; p = 2; }
            if f > val { val = f; p = 1; }
            if val <= 0 { val = 0; p = 3; }
            h_cur[j] = val;
            e_row[j] = if e > 0 { e } else { 0 };
            f_col = if f > 0 { f } else { 0 };
            ptr[i][j] = p;
            if val > best { best = val; best_i = i; best_j = j; }
        }
        std::mem::swap(&mut h_prev, &mut h_cur);
    }
    // traceback from (best_i, best_j)
    let mut q_aln = Vec::new();
    let mut t_aln = Vec::new();
    let mut i = best_i;
    let mut j = best_j;
    let mut identities = 0;
    let mut positives = 0;
    let mut gaps = 0;
    while i > 0 && j > 0 && ptr[i][j] != 3 {
        match ptr[i][j] {
            0 => {
                let qc = query[i - 1];
                let tc = target[j - 1];
                if qc == tc { identities += 1; }
                if BLOSUM62[aa_idx(qc)][aa_idx(tc)] > 0 { positives += 1; }
                q_aln.push(qc);
                t_aln.push(tc);
                i -= 1;
                j -= 1;
            }
            1 => { // gap in target: query residue vs '-'
                q_aln.push(query[i - 1]);
                t_aln.push(b'-');
                gaps += 1;
                i -= 1;
            }
            _ => { // gap in query
                q_aln.push(b'-');
                t_aln.push(target[j - 1]);
                gaps += 1;
                j -= 1;
            }
        }
    }
    let q_start = i + 1;
    let q_end = best_i;
    let t_start = j + 1;
    let t_end = best_j;
    q_aln.reverse();
    t_aln.reverse();
    let q_s = String::from_utf8(q_aln.clone()).unwrap();
    let t_s = String::from_utf8(t_aln.clone()).unwrap();
    let mut mid = String::with_capacity(q_s.len());
    for (a, b) in q_aln.iter().zip(t_aln.iter()) {
        if a == b { mid.push(*a as char); }
        else if *a != b'-' && *b != b'-' && BLOSUM62[aa_idx(*a)][aa_idx(*b)] > 0 {
            mid.push('+');
        } else { mid.push(' '); }
    }
    Alignment { score: best, q_start, q_end, t_start, t_end,
                q_aln: q_s, midline: mid, t_aln: t_s,
                identities, positives, gaps }
}

thread_local! {
    static DB: std::cell::RefCell<Vec<Target>> = const { std::cell::RefCell::new(Vec::new()) };
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn hit_json(h: &Hit) -> String {
    format!(
        "{{\"gene\":\"{}\",\"species\":\"{}\",\"desc\":\"{}\",\
          \"score\":{},\"bits\":{:.1},\"evalue\":{:.3e},\
          \"identity\":{:.1},\"positive\":{:.1},\"gaps\":{},\"aln_len\":{},\
          \"q_start\":{},\"q_end\":{},\"t_start\":{},\"t_end\":{},\
          \"q_aln\":\"{}\",\"midline\":\"{}\",\"t_aln\":\"{}\"}}",
        esc(&h.gene), esc(&h.species), esc(&h.desc),
        h.score, h.bits, h.evalue, h.identity, h.positive, h.gaps, h.aln_len,
        h.q_start, h.q_end, h.t_start, h.t_end,
        esc(&h.q_aln), esc(&h.midline), esc(&h.t_aln))
}

#[wasm_bindgen]
pub fn init_db(entries: &js_sys::Array) -> usize {
    let mut db = Vec::new();
    for v in entries.iter() {
        let o = js_sys::Object::from(v);
        let get = |k: &str| -> String {
            js_sys::Reflect::get(&o, &JsValue::from_str(k))
                .ok().and_then(|v| v.as_string()).unwrap_or_default()
        };
        let seq_raw = get("q").to_uppercase();
        let seq: Vec<u8> = seq_raw.bytes()
            .filter(|c| c.is_ascii_uppercase()).collect();
        db.push(Target { gene: get("g"), species: get("s"),
                         desc: get("n"), seq });
    }
    let n = db.len();
    DB.with(|d| *d.borrow_mut() = db);
    n
}

#[derive(Clone)]
struct Hit {
    gene: String,
    species: String,
    desc: String,
    score: i32,
    bits: f64,
    evalue: f64,
    identity: f64,
    positive: f64,
    gaps: i32,
    aln_len: i32,
    q_start: i32,
    q_end: i32,
    t_start: i32,
    t_end: i32,
    q_aln: String,
    midline: String,
    t_aln: String,
}

#[wasm_bindgen]
pub fn search(query: &str, max_hits: usize) -> js_sys::Array {
    let q: Vec<u8> = query.to_uppercase().bytes()
        .filter(|c| c.is_ascii_uppercase()).collect();
    let m = q.len() as f64;
    let out = js_sys::Array::new();
    if q.len() < 5 { return out; }
    DB.with(|db| {
        let db = db.borrow();
        let db_residues: f64 = db.iter().map(|t| t.seq.len() as f64).sum();
        let mut hits: Vec<(Alignment, &Target)> = db.iter()
            .filter_map(|t| {
                let a = sw(&q, &t.seq, 11, 1);
                if a.score > 0 { Some((a, t)) } else { None }
            })
            .collect();
        hits.sort_by(|a, b| b.0.score.cmp(&a.0.score));
        for (a, t) in hits.into_iter().take(max_hits) {
            let bits = (LAMBDA * a.score as f64 - K_PARAM.ln()) / std::f64::consts::LN_2;
            let evalue = m * db_residues * (-LAMBDA * a.score as f64).exp() * K_PARAM;
            let aln_len = a.q_aln.len().max(1) as f64;
            let h = Hit {
                gene: t.gene.clone(),
                species: t.species.clone(),
                desc: t.desc.clone(),
                score: a.score,
                bits,
                evalue: evalue.max(0.0),
                identity: a.identities as f64 / aln_len * 100.0,
                positive: a.positives as f64 / aln_len * 100.0,
                gaps: a.gaps as i32,
                aln_len: a.q_aln.len() as i32,
                q_start: a.q_start as i32,
                q_end: a.q_end as i32,
                t_start: a.t_start as i32,
                t_end: a.t_end as i32,
                q_aln: a.q_aln,
                midline: a.midline,
                t_aln: a.t_aln,
            };
            out.push(&JsValue::from_str(&hit_json(&h)));
        }
    });
    out
}
