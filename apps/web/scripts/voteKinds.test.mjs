import assert from 'node:assert/strict';
import { test } from 'node:test';
import { candidateIn, repeatsKind, sameElection, voteKind } from '../src/lib/voteKinds.ts';

const v = (title_he, question_he = 'לאשר את ההצעה', motion_type = 'other') => voteKind({ title_he, question_he, motion_type });

test('term-start votes: the Speaker, the deputies, the Arrangements Committee and its proposals', () => {
  assert.equal(v('בחירת יושב-ראש הכנסת', 'לקבל את הצעת הוועדה המסדרת', 'procedural'), 'speaker');
  assert.equal(v('בחירת יושב ראש הכנסת ה-25'), 'speaker');
  assert.equal(v('המלצת הוועדה המסדרת לבחירת סגנים זמניים ליושב ראש הכנסת - הצבעה', 'לקבל את הצעת הוועדה המסדרת', 'procedural'), 'deputies');
  assert.equal(v('בחירת הוועדה המסדרת לפי סעיף 2א לחוק הכנסת, התשנ"ד-1994'), 'arrangements');
  assert.equal(v('הודעת חבר הכנסת זאב אלקין בדבר הרכב הוועדה המסדרת - הצבעה', 'לקבל את ההצעה בדבר הרכב הוועדה המסדרת', 'procedural'), 'arrangements');
  assert.equal(v('הודעת יושב-ראש הוועדה המסדרת בדבר הרכב ועדות הכנסת הקבועות', 'לקבל את הצעת הוועדה המסדרת', 'procedural'), 'arrangementsProposal');
});

test('continuity, government decisions and agenda motions', () => {
  assert.equal(v('הודעת הממשלה על רצונה להחיל דין רציפות על הצעות חוק', 'להחיל דין רציפות על הצעת החוק', 'procedural'), 'continuity');
  assert.equal(v('הודעת הממשלה בהתאם לסעיף 31(ב) לחוק-יסוד: הממשלה להעביר לראש הממשלה את הסמכויות'), 'government');
  assert.equal(v('הודעת הממשלה על צירוף שר לממשלה ועל שינוי בחלוקת התפקידים בין השרים', 'לקבל את הודעת הממשלה'), 'government');
  assert.equal(v('הצעה לסדר-היום בנושא: הארועים בהר הבית', 'לכלול את הנושא בסדר-היום של הכנסת', 'agenda'), 'agenda');
  assert.equal(v('הבנות ג\'נבה', 'לקבל את הצעת סיכום הדיון', 'agenda'), 'agendaSummary');
});

test('anything else gets no explanation rather than a guess', () => {
  assert.equal(v('הודעת הממשלה על פעילותה'), null);         // a government notice that needs no approval under §15 or §31
  assert.equal(v('הצעת ועדת הכנסת לתיקון סעיפים 34א\', 36א\' לתקנון הכנסת', 'לקבל את הצעת ועדת הכנסת', 'procedural'), null);
  assert.equal(v('הצעת חוק הממשלה (תיקון מס\' 3), התשס"ד-2004', 'הצבעה', 'adopt_bill'), null);
});

test('a Speaker\'s election held as several votes: the day\'s votes together, most votes first', () => {
  const vote = (id, n, title_he = 'בחירת יושב ראש הכנסת ה-26', occurred_on = '2026-11-17') => ({ id, title_he, occurred_on, roll_call: { for: n } });
  const katz = vote(46731, 52), kahana = vote(46730, 66);
  assert.deepEqual(sameElection(katz, [katz, vote(1, 90, 'בחירת יושב ראש הכנסת ה-25'), kahana, vote(2, 9, undefined, '2026-11-18')]).map((v) => v.id), [46730, 46731]);
  assert.deepEqual(sameElection(katz, [katz]).map((v) => v.id), [46731]);   // the only vote: an ordinary verdict
});

test('the candidate is the one MK a candidacy subject names', () => {
  const mks = [{ name_he: 'אופיר כץ' }, { name_he: 'מתן כהנא' }, { name_he: 'איתמר בן גביר' }, { name_he: 'דוד ביטן' }, { name_he: 'דוד ביטן כהן' }];
  assert.equal(candidateIn('מועמדותו של חבר הכנסת אופיר כץ', mks)?.name_he, 'אופיר כץ');
  assert.equal(candidateIn('ההצעה לבחור את חבר הכנסת מתן כהנא', mks)?.name_he, 'מתן כהנא');
  assert.equal(candidateIn('מועמדותו של חבר הכנסת איתמר בן-גביר', mks)?.name_he, 'איתמר בן גביר');   // a hyphen in the source
  assert.equal(candidateIn('מועמדותו של חבר הכנסת דוד ביטן כהן', mks)?.name_he, 'דוד ביטן כהן');       // the longer name
  assert.equal(candidateIn('הצעת חבר הכנסת אופיר כץ', mks), null);                                  // who proposed, not who stands
  assert.equal(candidateIn('הצעת חבר הכנסת אופיר כץ לבחור את חבר הכנסת מתן כהנא', mks), null);         // two names: no guess
  assert.equal(candidateIn('הצבעה', mks), null);
  assert.equal(candidateIn(null, mks), null);
});

test('a list explains a kind of vote once: the cards that follow of the same kind are brief', () => {
  const proposal = (what) => ({ title_he: `הצעת הוועדה המסדרת בעניין הקמת הוועדה המיוחדת ${what}`, question_he: 'לאשר את ההצעה', motion_type: 'other', bills: [] });
  const list = [proposal('לשוויון'), proposal('לנגב'), { title_he: 'בחירת יושב ראש הכנסת ה-26', bills: [] }, proposal('לפשיעה'),
    { title_he: 'הצעת חוק', bills: [{}] }, { title_he: 'הצעת חוק אחרת', bills: [{}] }];
  assert.deepEqual(list.map((_, i) => repeatsKind(list, i)), [false, true, false, false, false, false]);
});
