import type { Choice, Majority, MotionType, Stage } from "./api";

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
