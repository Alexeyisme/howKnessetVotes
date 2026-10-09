// k6 load test for the hkv stack (docs/deploy.md#capacity), started by run.sh. Env: BASE, MODE=hot|tail|mix,
// RATE (requests/s), DUR (e.g. 40s), SEED. pools.json (pools.py) holds the IDs of the database copy.
// hot: a link shared widely (a few pages); tail: crawlers (any page, any language); mix: half of each.
import http from "k6/http";
import { check } from "k6";
import { Counter } from "k6/metrics";

const errTimeout = new Counter("err_timeout"), err5xx = new Counter("err_5xx"), errOther = new Counter("err_other");

const pools = JSON.parse(open("./pools.json"));
const BASE = __ENV.BASE || "http://localhost:8088";
const MODE = __ENV.MODE || "mix";
const RATE = Number(__ENV.RATE || 10);
const DUR = __ENV.DUR || "40s";
const LANGS = ["ru", "he", "en", "ar"];
const W_LANG = ["ru", "ru", "he", "he", "he", "en", "ar"];   // visitors: mostly ru and he

// "hot": what a viral post sends people to — the home page, the vote lists, a few laws, parties, the quiz.
const HOT = [
  "/ru", "/he", "/ru", "/he", "/en",
  "/ru/votes", "/he/votes", "/ru/votes?view=contested", "/he/votes?view=contested",
  "/ru/match", "/he/match", "/ru/parties", "/ru/members", "/he/members", "/ru/topics",
  "/ru/search?q=%D0%BB%D0%B8%D0%BA%D1%83%D0%B4", "/he/search?q=%D7%9C%D7%99%D7%9B%D7%95%D7%93",
  ...pools.finalVotes.slice(0, 6).flatMap((v) => [`/ru/votes/${v}`, `/he/votes/${v}`]),
  ...pools.parties.slice(0, 6).flatMap((p) => [`/ru/parties/${p}`, `/he/parties/${p}`]),
  ...pools.members.slice(0, 6).map((m) => `/ru/members/${m}`),
];

let seed = Number(__ENV.SEED || 1) * 7919 + __VU * 104729;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
const pick = (xs) => xs[Math.floor(rnd() * xs.length)];

// "tail": what crawlers do — any vote, member, bill or party page in any language, mostly not cached yet.
function tail() {
  const l = pick(LANGS), r = rnd();
  if (r < 0.5) return `/${l}/votes/${pick(pools.votes)}`;
  if (r < 0.7) return `/${l}/members/${pick(pools.members)}${rnd() < 0.3 ? "?tab=all" : ""}`;
  if (r < 0.9) return `/${l}/bills/${pick(pools.bills)}`;
  if (r < 0.95) return `/${l}/factions/${pick(pools.factions)}`;
  return `/${l}/topics/${pick(pools.topics)}`;
}

export const options = {
  discardResponseBodies: true,
  scenarios: {
    load: { executor: "constant-arrival-rate", rate: RATE, timeUnit: "1s", duration: DUR, preAllocatedVUs: Math.max(20, RATE * 2), maxVUs: 2000 },
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

export default function () {
  const path = MODE === "hot" ? pick(HOT) : MODE === "tail" ? tail() : rnd() < 0.5 ? pick(HOT) : tail();
  const res = http.get(BASE + path.replace(/^\/ru/, `/${MODE === "tail" ? pick(LANGS) : pick(W_LANG)}`), { timeout: "15s", redirects: 0 });
  check(res, { ok: (r) => r.status === 200 });
  if (res.status === 0) errTimeout.add(1); else if (res.status >= 500) err5xx.add(1); else if (res.status !== 200) errOther.add(1);
}
