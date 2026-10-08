-- A visitor may leave a way to reach them (email, Telegram) with a correction or a mistake report, so the editor can
-- answer: the notification bot only delivers messages, it cannot reply. Optional and free text.
ALTER TABLE translation_suggestion
    ADD COLUMN contact text CHECK (length(contact) <= 200);
