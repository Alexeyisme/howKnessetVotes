import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isNumberedSubject, phrase, PHRASE_COUNT, subjectText } from '../src/i18n/content/votePhrases.ts';

test('the question is a closed list: known wordings in every language, Hebrew UI and unknown wordings untouched', () => {
  assert.equal(phrase('לאשר את ההצעה', 'ru'), 'Утвердить предложение');
  assert.equal(phrase('לקבל את הצעת החוק בקריאה שלישית', 'en'), 'To adopt the bill on third reading');
  assert.equal(phrase(' לקבל את ההסתייגות ', 'ar'), 'قبول التحفّظ');
  assert.equal(phrase('לאשר את ההצעה', 'he'), null);
  assert.equal(phrase('מועמדותו של חבר הכנסת אופיר כץ', 'ru'), null);
  assert.equal(phrase(null, 'ru'), null);
  assert.ok(PHRASE_COUNT >= 60);
});

test('numbered subjects are read by pattern', () => {
  assert.equal(subjectText('הסתייגות 12', 'ru'), 'Оговорка № 12');
  assert.equal(subjectText('ההסתייגות 12', 'en'), 'Reservation no. 12');
  assert.equal(subjectText("הסתייגות מס' 7", 'ru'), 'Оговорка № 7');
  assert.equal(subjectText('הסתייגות 12,267', 'ru'), 'Оговорка № 12,267');          // the source's thousands separator
  assert.equal(subjectText('הסתייגות 3 לסעיף 14', 'ru'), 'Оговорка № 3 к статье 14');
  assert.equal(subjectText('סעיף 1', 'ru'), 'Статья 1');
  assert.equal(subjectText('סעיף 4, כהצעת הוועדה', 'ru'), 'Статья 4 в редакции комиссии');
  assert.equal(subjectText('סעיפים 1–13', 'ru'), 'Статьи 1–13');
  assert.equal(subjectText('סעיפים 2-3', 'en'), 'Sections 2–3');
  assert.equal(subjectText('סעיפים 5 – 9 כהצעת הוועדה', 'en'), 'Sections 5–9 as proposed by the committee');
  assert.equal(subjectText('הסתייגויות לסעיף 20 לשנת התקציב 2025, בדבר תוספת תקציב', 'ru'), 'Оговорки к статье 20 на бюджетный год 2025: увеличение бюджета');
  assert.equal(subjectText('ההסתייגויות לסעיף 4 בדבר הפחתת תקציב', 'en'), 'The reservations to section 4: a budget cut');
  assert.equal(subjectText('קריאה שנייה', 'ru'), 'Второе чтение');                     // the legacy source: a closed-list wording
});

test('a subject that only resembles a pattern stays in Hebrew', () => {
  assert.equal(subjectText('הסתייגות 18 לחלופין', 'ru'), null);
  assert.equal(subjectText('הסתייגות (3) של חבר הכנסת שלמה קרעי לפני סעיף 2', 'ru'), null);
  assert.equal(subjectText('סעיף 12א', 'ru'), null);
  assert.equal(subjectText('סעיף 1', 'he'), null);
  assert.equal(isNumberedSubject('סעיף 1'), true);
  assert.equal(isNumberedSubject('קריאה שנייה'), false);
  assert.equal(isNumberedSubject(null), false);
});
