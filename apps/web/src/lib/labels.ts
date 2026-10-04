import type { Choice, Majority, MotionType, Stage, VoteDetail } from "./api";

export const STAGE: Record<Stage, string> = {
  preliminary: "Предварительное чтение",
  first: "Первое чтение",
  second: "Второе чтение",
  third: "Третье чтение",
  not_applicable: "Вне законодательных чтений",
  unknown: "Стадия не определена",
};

export const MOTION: Record<MotionType, string> = {
  adopt_bill: "Голосование за законопроект",
  reject_bill: "Снятие законопроекта с повестки",
  adopt_section: "Голосование по статьям законопроекта",
  reservation: "Голосование по оговорке (הסתייגות)",
  no_confidence: "Вотум недоверия правительству",
  agenda: "Предложение на повестку дня",
  secondary_legislation: "Подзаконный акт",
  procedural: "Процедурное решение",
  other: "Другое решение",
  unknown: "Тип вопроса не определён",
};

// What "for" means depends on the question; spelled out so a reservation vote is not read as support for the bill.
export const MOTION_HINT: Partial<Record<MotionType, string>> = {
  reservation: "«За» здесь — за принятие оговорки оппозиции или депутата, а не за законопроект в целом.",
  reject_bill: "«За» здесь — за снятие законопроекта с повестки.",
  no_confidence: "«За» здесь — за выражение недоверия правительству.",
  adopt_section: "«За» здесь — за принятие перечисленных статей во втором чтении.",
};

export const METHOD: Record<string, string> = {
  electronic: "электронное",
  roll_call: "поимённое",
  show_of_hands_counted: "поднятием рук, с подсчётом",
  show_of_hands: "поднятием рук",
  secret: "тайное",
  unknown: "способ неизвестен",
};

export const CHOICE: Record<Choice, string> = { for: "за", against: "против", abstain: "воздержался" };

export const PARTICIPATION: Record<string, string> = {
  cast: "проголосовал",
  present_not_voting: "присутствовал, не голосовал",
  participated_choice_unavailable: "голосовал, выбор неизвестен",
  absent_reported: "отмечен как отсутствующий",
  declared_nonparticipation: "заявил о неучастии",
  unknown: "неизвестный код",
};

export const MAJORITY: Record<Majority, string> = {
  for: "большинство за",
  against: "большинство против",
  abstain: "большинство воздержалось",
  mixed: "нет большинства",
  none: "не голосовали",
};

export function ballotLabel(choice: Choice | null, participation: string): string {
  return choice ? CHOICE[choice] : PARTICIPATION[participation] ?? participation;
}

const dateFmt = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jerusalem" });
const timeFmt = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jerusalem" });

export function formatDate(isoDate: string): string {
  return dateFmt.format(new Date(`${isoDate}T12:00:00+02:00`));
}

export function formatTime(iso: string | null): string | null {
  return iso ? timeFmt.format(new Date(iso)) : null;
}

// Methods that never produce a roll-call list; for any other method zero records means "not loaded (yet)".
const NO_ROLL_CALL = new Set(["show_of_hands", "show_of_hands_counted", "secret"]);

export function missingRollCallText(method: string): string {
  return NO_ROLL_CALL.has(method)
    ? `поимённого списка не бывает: голосование ${METHOD[method] ?? method}`
    : "поимённые данные ещё не загружены или отсутствуют в источнике";
}

export function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

export function percent(r: { numerator: number; denominator: number; value: number | null }): string {
  return r.value == null ? "—" : `${(r.value * 100).toLocaleString("ru-RU", { maximumFractionDigits: 1 })}%`;
}

export function period(from: string, to: string | null): string {
  return `${formatDate(from)} — ${to ? formatDate(to) : "по настоящее время"}`;
}

export const ORIGIN: Record<string, string> = { private: "частный", government: "правительственный", committee: "комиссии" };

export const INITIATOR_ROLE: Record<string, string> = { initiator: "инициатор", joined: "присоединился", withdrew: "отозвал подпись" };

/** In RTL text an en dash / maqaf between digits is bidi-neutral and flips the range ("15–16" shows as "16–15");
 *  a hyphen-minus between digits is a European separator and keeps the order. */
export function bidiSafe(s: string): string {
  return s.replace(/(\d)\s*[–—־]\s*(\d)/g, "$1-$2");
}

// What each stage means, in one plain sentence (vote page, glossary).
export const STAGE_HINT: Partial<Record<Stage, string>> = {
  preliminary: "Первое голосование по законопроекту депутата: Кнессет решает, стоит ли вообще его рассматривать. После него текст готовит комиссия.",
  first: "Голосование по законопроекту после подготовки в комиссии (или по правительственному законопроекту сразу). Если принят — возвращается в комиссию на доработку.",
  second: "Голосование по статьям окончательного текста и по оговоркам (поправкам) к ним. Обычно проходит в тот же день, что и третье чтение.",
  third: "Окончательное голосование. Если законопроект принят в третьем чтении, он становится законом.",
};

// Only votes on a bill as a whole and no-confidence motions: what most readers mean by "how did they vote".
export const MAIN_MOTIONS: MotionType[] = ["adopt_bill", "no_confidence"];

/** One-line outcome in plain words. Official result when published (votes up to 2021-07), otherwise derived from the
 *  roll call: simple majority of for over against (a tie is not adopted); no-confidence needs 61 votes for. */
export function verdict(v: VoteDetail): { text: string; accepted: boolean | null; derived: boolean } | null {
  const rc = v.roll_call;
  let accepted: boolean | null = v.official_totals?.is_accepted ?? null;
  const derived = accepted == null;
  if (derived) {
    if (rc.total_records === 0 || rc.for + rc.against === 0) return null;
    accepted = v.motion_type === "no_confidence" ? rc.for >= 61 : rc.for > rc.against;
  }
  const yes = accepted;
  const stage = v.stage;
  const text = (() => {
    switch (v.motion_type) {
      case "adopt_bill":
        if (stage === "third") return yes ? "Закон принят" : "Закон не принят";
        if (stage === "first") return yes ? "Законопроект прошёл первое чтение" : "Законопроект не прошёл первое чтение";
        if (stage === "preliminary") return yes ? "Законопроект прошёл предварительное чтение" : "Законопроект не прошёл предварительное чтение";
        return yes ? "Законопроект одобрен" : "Законопроект не одобрен";
      case "reservation": return yes ? "Оговорка принята" : "Оговорка отклонена";
      case "adopt_section": return yes ? "Статьи приняты" : "Статьи отклонены";
      case "no_confidence": return yes ? "Вотум недоверия принят" : "Вотум недоверия не прошёл";
      case "reject_bill": return yes ? "Законопроект снят с повестки" : "Законопроект не снят с повестки";
      default: return yes ? "Предложение принято" : "Предложение отклонено";
    }
  })();
  return { text, accepted, derived };
}
