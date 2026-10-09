import type { Majority, MotionType, Stage } from "@/lib/api";
import type { Dict } from "./ru";

const s = (n: number, one: string, many: string) => (n === 1 ? one : many);
const ord = (n: number) => {
  const m100 = n % 100, m10 = n % 10;
  return `${n}${m100 >= 11 && m100 <= 13 ? "th" : m10 === 1 ? "st" : m10 === 2 ? "nd" : m10 === 3 ? "rd" : "th"}`;
};

export const en: Dict = {
  site: {
    name: "How the Knesset Votes",
    description: "Roll-call votes in the Knesset plenum: how every party and member voted on each bill, with a source for every number.",
  },
  nav: {
    label: "Sections", votes: "Votes", topics: "Topics", bills: "Bills", members: "Members", factions: "Parties",
    searchLabel: "Search", searchPh: "Search: topic, bill, member", language: "Language",
    match: "Who votes like me",
    compare: "Compare",
  },
  footer: {
    asOf: (updated, last, votes, ballots) => `Data updated ${updated}; latest vote ${last}. ${votes} votes, ${ballots} roll-call records.`,
    sources: "Sources: Knesset open data, the Knesset website (member names and photos), Wikidata,",
    oknesset: "Open Knesset",
    methodology: "Methodology", glossary: "Glossary", translation: "About the translation", api: "API",
    report: "Write to the author",
  },
  common: {
    show: "Show", find: "Search", nothingFound: "Nothing found.", noVotes: "No votes.", earlier: "Earlier →",
    term: (n) => `${ord(n)} Knesset`,
    knessetOf: (n) => `the ${ord(n)} Knesset`,
    allTerms: "All Knessets", termLabel: "Knesset", present: "present", all: "All",
    rateDetail: (num, den, unit) => `${num} of ${den} ${unit}`,
    billsCount: (n) => `${n} ${s(n, "bill", "bills")}`,
    votesCount: (n) => `${n} ${s(n, "vote", "votes")}`,
    lastVote: (d) => `latest ${d}`,
    passedThird: "passed third reading", passed: "passed",
    factionUnknown: "party unknown",
    glossaryLink: "Glossary →",
    sourceKnesset: "Source:",
    machine: "automatic translation", suggest: "suggest a correction", report: "write to the author",
    hebrewOriginal: "Hebrew original",
  },
  stage: {
    preliminary: "Preliminary reading", first: "First reading", second: "Second reading", third: "Third reading",
    not_applicable: "Not a legislative reading", unknown: "Stage unknown",
  } as Record<Stage, string>,
  stageHint: {
    preliminary: "The first vote on a member's bill: the Knesset decides whether to consider it at all. A committee then prepares the text.",
    first: "A vote on the bill after committee preparation (government bills start here). If it passes, it goes back to committee for further work.",
    second: "Votes on the sections of the final text and on reservations (amendments) to them. Usually held the same day as the third reading.",
    third: "The final vote. A bill that passes its third reading becomes law.",
  },
  motion: {
    adopt_bill: "Vote on the bill", reject_bill: "Removing the bill from the agenda",
    adopt_section: "Vote on sections of the bill", reservation: "Vote on a reservation (amendment)",
    no_confidence: "No-confidence motion", agenda: "Motion for the agenda", secondary_legislation: "Secondary legislation",
    procedural: "Procedural decision", other: "Other decision", unknown: "Question type unknown",
  } as Record<MotionType, string>,
  motionHint: {
    reservation: "“For” here means for the reservation (an amendment, usually by the opposition), not for the bill as a whole.",
    reject_bill: "“For” here means for removing the bill from the agenda.",
    no_confidence: "“For” here means for no confidence in the government.",
    adopt_section: "“For” here means for adopting the listed sections in second reading.",
  },
  method: {
    electronic: "electronic", roll_call: "roll call", show_of_hands_counted: "show of hands, counted",
    show_of_hands: "show of hands", secret: "secret ballot", unknown: "method unknown",
  },
  methodBadge: (m) => `${m} vote`,
  choice: { for: "for", against: "against", abstain: "abstained" },
  choiceShort: { for: "for", against: "against", abstain: "abst." },
  participation: {
    cast: "voted", present_not_voting: "present, did not vote", participated_choice_unavailable: "voted, choice unknown",
    absent_reported: "reported absent", declared_nonparticipation: "declared non-participation", unknown: "unknown code",
  },
  majority: { for: "majority for", against: "majority against", abstain: "majority abstained", mixed: "no majority", none: "did not vote" } as Record<Majority, string>,
  origin: { private: "Private member's", government: "Government", committee: "Committee" },
  initiatorRole: { initiator: "sponsor", joined: "joined", withdrew: "withdrew" },
  verdict: (motion, stage, yes) => {
    switch (motion) {
      case "adopt_bill":
        if (stage === "third") return yes ? "Law passed" : "Law not passed";
        if (stage === "first") return yes ? "Bill passed first reading" : "Bill failed first reading";
        if (stage === "preliminary") return yes ? "Bill passed preliminary reading" : "Bill failed preliminary reading";
        return yes ? "Bill approved" : "Bill not approved";
      case "reservation": return yes ? "Reservation adopted" : "Reservation rejected";
      case "adopt_section": return yes ? "Sections adopted" : "Sections rejected";
      case "no_confidence": return yes ? "No-confidence motion passed" : "No-confidence motion failed";
      case "reject_bill": return yes ? "Bill removed from the agenda" : "Bill not removed from the agenda";
      default: return yes ? "Motion adopted" : "Motion rejected";
    }
  },
  rc: {
    for: "For", against: "Against", abstained: "Abstained", present: "Present, did not vote",
    line: (f, a, ab) => `${f} for · ${a} against${ab ? ` · ${ab} abst.` : ""}`,
    noList: (method) => `no roll call exists: ${method} vote`,
    notLoaded: "roll-call data not loaded yet or missing from the source",
    noRollCall: "no roll call",
    cast120: (n) => `${n} of 120 voted`,
  },
  home: {
    title: "How the Knesset Votes",
    lead: "How every party and member of Israel's parliament voted on each bill — from official Knesset data, in English, Russian, Hebrew and Arabic.",
    searchPh: "Member, party, topic or bill — in any language",
    examples: "Try:",
    // one member, one party and two topics are shown at random on each visit; every one was checked to return results
    exampleQueries: {
      members: [
        "Netanyahu", "Lapid", "Gantz", "Bennett", "Lieberman", "Deri", "Gafni", "Smotrich", "Sa'ar", "Edelstein",
        "Merav Michaeli", "Mansour Abbas", "Ayman Odeh", "Tibi", "Shaked", "Kahlon", "Olmert", "Tzipi Livni", "Yachimovich", "Amir Peretz",
      ],
      parties: [
        "Likud", "Yesh Atid", "Shas", "Yisrael Beiteinu", "United Torah Judaism", "Labor", "Meretz", "Ra'am", "Hadash", "Blue and White",
      ],
      topics: [
        "budget", "draft", "housing", "education", "health", "pensions", "transport", "public transport", "environment", "water",
        "agriculture", "tourism", "culture", "sport", "elections", "Jerusalem", "immigration", "taxes", "army", "police",
        "disability", "energy", "children", "elderly", "students", "communications", "banking", "local authorities", "Negev", "Galilee",
      ],
    },
    topicsTitle: "How parties voted by topic",
    topicsAll: "All topics →",
    finalTitle: "Latest final votes",
    finalAll: "All votes →",
    contestedTitle: "Laws the coalition and opposition fought over",
    recess: (d) => `The Knesset is in recess: the 26th Knesset convenes on ${d}.`,
    latestVote: (d) => `Latest vote ${d}`,
    browse: "Browse",
    tiles: [
      { href: "/match", title: "Who votes like me?", text: "12 contested laws: answer, and see which party voted the way you would" },
      { href: "/compare", title: "Compare", text: "Two parties or two members: how often they vote the same way" },
      { href: "/members", title: "Members", text: "How each member voted, and when they broke with their party" },
      { href: "/factions", title: "Parties", text: "Members, cohesion and votes of each party" },
      { href: "/bills", title: "Bills", text: "Every vote on a bill, from preliminary to third reading" },
      { href: "/votes", title: "All votes", text: "The plenum vote feed, filtered by stage" },
    ],
  },
  votes: {
    title: "Plenum votes",
    filtersLabel: "Which votes to show",
    filters: { main: "Main", contested: "Contested", final: "Final (third reading)", first: "First reading", preliminary: "Preliminary", all: "All votes" },
    lead: {
      main: "Votes on bills as a whole and no-confidence motions. Reservations, sections and procedural votes are under “All votes”.",
      final: "Votes after which a bill becomes law (or does not).",
      contested: "Final votes where the coalition majority and the opposition majority voted differently, with at least 60 members voting: the laws that were fought over.",
      all: "All votes, including reservations (amendments), individual sections and procedural decisions.",
    },
  },
  vote: {
    meta: (date, term, id) => `${date} · ${ord(term)} Knesset · vote no. ${id}`,
    status: (st) => `status: ${st}`,
    derived: " — counted from roll-call records (no official result is published)",
    official: " — official Knesset result",
    resultLine: (f, a, ab) => `: ${f} for, ${a} against${ab ? `, ${ab} abstained` : ""}`,
    quorum: (cast) => `${cast} of 120 members voted. The plenum has no quorum: a decision passes by a simple majority of those voting. A special majority (61 votes) is needed only for no-confidence motions and some provisions of Basic Laws.`,
    question: "What was put to the vote",
    bill: "Bill:",
    aboutBill: "About the law and the debate",
    debateMore: "All arguments and speakers are on the bill page",
    resultTitle: "Result from roll-call records",
    noRecords: (why) => `No roll-call records: ${why}.`,
    officialTotals: (f, a, ab) => `Official result: ${f} for, ${a} against, ${ab} abstained`,
    officialAccepted: " — adopted.", officialRejected: " — rejected.",
    excluded: (n) => ` According to the source, ${n} roll-call ${s(n, "record was", "records were")} not counted in the official result (vote declared or corrected after the vote).`,
    totalsMatch: " Taking that into account, the roll call matches the official result.",
    totalsMismatch: " The roll call differs from the official result — the discrepancy is logged for review.",
    onlyRecords: "Only members with a record are counted. No record does not mean the member was absent.",
    noOfficial: " Official results for votes after July 2021 are not published in the open data.",
    byFaction: "By party on the day of the vote",
    unresolved: (n) => `${n} ${s(n, "record has", "records have")} no known party on this date.`,
    table: (n) => `Roll call (${n})`,
    sourceLink: "vote page on the Knesset website ↗",
    numbers: "Numbers and sources",
  
    notFound: "Vote not found", notFoundText: "It may not be loaded yet.", backToList: "Back to votes",
  },
  breakdown: {
    legend: "Legend", for: "for", abstain: "abstained", against: "against",
    counts: (c) => {
      const p = [`${c.for} for`, `${c.against} against`];
      if (c.abstain) p.push(`${c.abstain} abst.`);
      if (c.present_not_voting) p.push(`${c.present_not_voting} present, not voting`);
      if (c.other) p.push(`${c.other} other`);
      return p.join(" · ");
    },
    ambiguous: (n) => ` · ${n} ambiguous`,
    ambiguousTitle: "Voted on the day of a party switch: membership is ambiguous",
    factionPage: "Party page →",
  },
  ballots: {
    member: "Member", factionThen: "Party at the time", vote: "Vote", code: "Source code",
    filterName: "Name", filterNamePh: "Filter by name", filterFaction: "Party", allFactions: "All parties",
    deviates: "Only votes against own party's majority",
    deviatesMark: "against party majority",
    shown: (n, total) => `Showing ${n} of ${total}`,
    notCounted: "not in official result",
  },
  members: {
    title: "Members", searchPh: "Name in any language, e.g. Lapid",
    searchAll: (n) => `Search across all Knessets: ${n}`,
    termCount: (term, n) => `${ord(Number(term))} Knesset: ${n} members with roll-call votes`,
    member: "Member", lastFaction: "Latest party", terms: "Knessets", records: "Roll-call records",
  },
  member: {
    kicker: (terms) => `Member of Knesset · Knessets ${terms}`,
    currentFaction: "Party:", lastFaction: "Latest party:",
    photoCredit: "Photo: Knesset website",
    withCoalition: "Voted with the coalition", withCoalitionUnit: "votes where the coalition had a majority",
    compareLink: "Compare with another member →", topicFilter: "Topic",
    summary: (p) => <>Voted in <strong>{p.part}</strong> of roll-call votes held during their mandate ({p.cast} of {p.avail}).
      {" "}Voted differently from their party&apos;s majority <strong>{p.dev} {s(p.dev, "time", "times")}</strong> out of {p.comparable} comparable votes.
      {p.initiated > 0 && <> Sponsored {p.initiated} {s(p.initiated, "bill", "bills")} that reached a plenum vote.</>}</>,
    participation: "Roll-call participation", participationUnit: "votes during the mandate",
    deviation: "Voted differently from party majority", deviationUnit: "comparable votes",
    bills: "Bills that reached a vote", billsDetail: (n) => `as sponsor; joined ${n} more`,
    note: "Statistics cover votes since 20 October 2003. Participation is the share of roll-call votes during the mandate in which the member voted for, against or abstained. It is not attendance. The party majority is computed from the other members of the party who voted that time (at least two); voting differently does not mean breaking party discipline.",
    factions: "Parties", faction: "Party", term: "Knesset", period: "Period",
    votes: "Votes", tabFinal: "Final votes", tabAll: "All", tabDeviated: "Against party majority",
    finalHint: "Third-reading votes on bills as a whole: after these, a bill becomes law.",
    noVotes: "No votes.",
  },
  factions: {
    title: "Factions by Knesset",
    lead: "A faction is a group of members in a given Knesset; one faction can include several parties. Votes are attributed to the faction on the day of the vote.",
    faction: "Party", period: "Period", membersEver: "Members (all time)", records: "Roll-call records",
  },
  faction: {
    kicker: (term, period) => `Party in the ${ord(term)} Knesset · ${period}`,
    titleWithTerm: (name, term) => `${name} (${ord(term)} Knesset)`,
    votesWithMembers: "Votes with members voting",
    cohesion: "Cohesion", cohesionUnit: "votes matched the party's most common choice",
    unanimous: "Voted unanimously", unanimousUnit: "votes (with two or more voting)",
    members: (n) => `Members (${n} all time)`, former: (n) => `Former members (${n})`,
    votes: "Votes", tabAll: "All", tabSplit: "Party split",
    party: "Party:", allKnessets: "all Knessets →",
    coalitionTitle: "Coalition and opposition", government: (n) => `Government ${n}`, curated: "corrected by hand",
  },
  bills: {
    title: "Bills", searchPh: "A word from the Hebrew title, or a number", onlyPassed: "only passed in third reading",
    lead: "Bills the plenum voted on, most recently voted first.",
  },
  bill: {
    kicker: (origin, term) => `${origin} bill · ${ord(term)} Knesset`,
    published: (d) => ` · published as law ${d}`,
    status: "Status:", topics: "Topics:",
    summaryTitle: "Official summary of the law (Knesset)",
    explanationTitle: "What the sponsors propose",
    explanationNote: "An automatic summary of the explanatory notes written by the bill's sponsors. These are their arguments, not an official Knesset summary.",
    explanationSource: "The bill on the Knesset website",
    officialTitle: (e) => `official classification of the law: ${e}`,
    ruleTitle: (e) => `from the word “${e}” in the title`,
    officialNote: " · * from the Knesset's official law classification",
    ruleNote: " · no asterisk — automatically from words in the title",
    initiators: "Sponsors", also: "Also:",
    timeline: (n) => `All plenum votes (${n})`,
    timelineHint: "In order. Votes on reservations and individual sections are shown separately from the vote on the bill as a whole.",
    related: "Related bills",
    milestones: "Readings",
    otherVotes: (n) => `Reservations, sections and other votes (${n})`,
    sourceLink: "bill page in the Knesset legislation database ↗",
    debateTitle: "What was said in the plenum",
    debateFor: "Arguments for", debateAgainst: "Arguments against", debateNone: "None were made.",
    debateNote: "An automatic summary of the plenum transcripts: the debate on the bill at every reading it was voted on. Arguments are given as the speakers made them; this is not an assessment. The list of speakers comes from the transcript, without a model.",
    debateTruncated: "A very long debate: every speech was shortened to the same length before summarising.",
    debateSources: (n) => (n === 1 ? "Transcript of the sitting" : "Transcripts of the sittings"),
    debateSpeakers: (n) => `Who spoke (${n})`,
    debateCols: { member: "Member", faction: "Faction", readings: "Readings", speeches: "Speeches", final: "In the final vote" },
    noRecord: "no record",
    reservationsTitle: "Reservations to the second reading",
    reservationsLead: (n) => `${n} ${s(n, "reservation was", "reservations were")} filed: proposed changes to the text the committee brought to the second and third reading.`,
    reservationsNone: "No reservations were filed to this bill.",
    reservationsByFaction: "By faction",
    reservationsCount: (n, m) => `${n} ${s(n, "reservation", "reservations")} · ${m} ${s(m, "member", "members")}`,
    reservationsJoint: "A joint reservation counts for every faction whose members filed it.",
    reservationsGroups: "Who proposed what",
    reservationsSections: "Sections:",
    reservationsSpeak: "Asked to speak:",
    reservationsUnresolved: (n) => `${n} ${s(n, "proposer was", "proposers were")} not matched to a member: listed under the groups, not counted by faction.`,
    reservationsNote: "Proposers and reservation numbers are extracted automatically from the committee version, and the count is checked against the numbers printed in it. The descriptions are an automatic summary.",
    reservationsUnchecked: "The reservation numbers in this document cannot be read as text, so the count was not checked against it automatically.",
    reservationsSource: "Committee version for the second and third reading (PDF)",
  },
  topics: {
    title: "Topics",
    note: "Topics come from the Knesset's official law classification and from words in the bill title; they have not been reviewed by an editor yet. A bill can belong to several topics.",
  },
  topic: {
    kicker: "Topic", aliases: "Also found by:",
    votesTitle: "Votes on bills in this topic",
    bills: (n) => `Bills in this topic (${n})`,
    lastVote: (d) => ` · latest vote ${d}`,
    allBills: "All bills in this topic →",
  },
  search: {
    title: "Search", ph: "Name, party, topic, bill title or number",
    hint: "Members, parties and topics can be searched in English, Russian, Hebrew or Arabic (e.g. “netanyahu”, “likud”, “transport”). Bills by the words of their title in any form (“tax” also finds “taxation”); in Hebrew, typos tolerated. A number finds a bill.",
    topics: "Topics", factions: "Parties", members: "Members", bills: "Bills",
    billsShown: (n, total) => `The latest ${n} of ${total.toLocaleString("en-GB")}: add a word to narrow the search`,
  },
  glossary: {
    title: "Glossary",
    lead: "Terms used on the vote pages, in plain words. Next to each is the Hebrew term as it appears in Knesset documents.",
    description: "Knesset terms in plain words: readings, reservations, parties, no-confidence motions.",
  },
  methodology: {
    title: "Methodology and sources",
    description: "Where the data comes from, how the numbers are computed and what they do not mean.",
  },
  alignment: { coalition: "coalition", opposition: "opposition", external_support: "outside support", unknown: "no government yet" },
  blocs: {
    title: "Coalition and opposition",
    line: (c, o) => `Coalition: ${c.for} for, ${c.against} against · Opposition: ${o.for} for, ${o.against} against`,
    contested: "Coalition and opposition voted differently",
    note: "A faction is in the coalition when one of its members holds a government post on the vote date (official Knesset data).",
    short: (c, o) => `Coalition ${c.for}:${c.against} · Opposition ${o.for}:${o.against}`,
  },
  sides: {
    for: "Supporters said", against: "Opponents said",
    made: (n) => `Speakers who made this point: ${n}`,
    counts: (speakers, reservations) => [
      speakers ? `${speakers} ${s(speakers, "member", "members")} spoke` : null,
      reservations ? `${reservations.toLocaleString("en-GB")} ${s(reservations, "reservation", "reservations")}` : null,
    ].filter(Boolean).join(" · "),
    note: "An automatic summary of the plenum debate: the argument each side made most often.",
    speeches: (n) => `Speeches in the debate: ${n}`,
  },
  parties: {
    title: "Parties",
    lead: "Each party across Knessets: the list it ran as each time, how many members it had, and whether it was in the coalition. A joint list counts for every party in it.",
    knessets: (n) => `${n} ${n === 1 ? "Knesset" : "Knessets"}`,
    byTerm: "Factions by Knesset →",
    faction: "Faction", term: "Knesset", period: "Period", members: "Members", role: "Coalition / opposition",
    kicker: "Party across Knessets",
    current: (term) => `In the ${ord(term)} Knesset`,
    finalVotes: "Final votes: how the list's majority voted",
    history: "Across Knessets",
    allVotes: "All votes of the list →",
  },
  compare: {
    title: "Compare",
    lead: "Two parties or two members: how often they voted the same way on bills as a whole and no-confidence motions, and the votes where they differed.",
    parties: "Parties", members: "Members", pick: "Choose two to compare.",
    agreement: "Voted the same way", agreementUnit: "shared votes",
    differences: (n) => `Votes where they differed (${n})`,
  },
  match: {
    title: "Who votes like me?",
    lead: (n, term) => `The ${n} final votes of the ${ord(term)} Knesset where the coalition and opposition split, with the most members voting. Say how you would have voted and see which party voted the same way. Nothing is stored.`,
    question: "Would you have passed this law?", yes: "For", no: "Against", skip: "Skip",
    progress: (i, n) => `${i} of ${n}`,
    resultTitle: "Parties that voted like you",
    agree: (n, m) => `agrees with you on ${n} of ${m}`,
    noAnswers: "You skipped every vote.",
    again: "Start over", share: "Share your result", copied: "Link copied",
    yours: "Your answer", passed: "Outcome",
  },
  suggest: {
    title: "Suggest a correction",
    lead: "Titles and summaries are translated automatically and marked as such. A correction goes to an editor; nothing changes on the site until they accept it. No account needed.",
    original: "Original", textLabel: "Corrected translation", noteLabel: "Note (optional)",
    send: "Send", thanks: "Thank you! The correction has been passed to an editor.", error: "Could not send. Please try again later.", back: "Back",
    reportTitle: "Write to the author",
    reportLead: "Hi! I'm Alexey. I built this site because I wanted this information myself; if it is useful to you too, welcome. Write to me: I read every message and I'm glad of kind words, ideas and questions, as well as notes on anything inaccurate. No account needed.",
    reportTextLabel: "Your message",
    contactLabel: "How to reply to you (email or Telegram, optional)",
    reportThanks: "Thank you! Your message has reached me.",
  },
  translation: { beta: null, more: "How the site is translated" },
  notFound: { title: "Page not found", text: "This page does not exist.", home: "Home" },
};
