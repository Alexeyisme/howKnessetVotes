import assert from 'node:assert/strict';
import { test } from 'node:test';
import { voteKind } from '../src/lib/voteKinds.ts';

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
