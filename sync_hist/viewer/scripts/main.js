// Entry point: call render(pivot(DATA)) after embedding your data.
// DATA must be an array of row objects with fields:
//   user, name, utac, topic, prob, cell_type, lang, cmd, status

main();

// -- Step 1: pivot -------------------------------------------------------------
//
// Transforms flat rows into:
//   users        : [{ user, name, utac }, ...]
//   columns      : [{ topic, prob }, ...]
//   colKeys      : ["topic\0prob", ...]
//   cells        : { userId: { colKey: summary } }
//   colSummaries : { colKey: { N, totalHey, perLang } }  -- aggregate over users
//   rowSummaries : { userId: { N, totalHey, perLang } }  -- aggregate over problems
//
// summary = {
//   hey     : number,
//   write   : { lang: count },
//   compile : { lang: { ok, err } },
//   run     : { lang: { ok, err } },
//   other   : { lang: { ok, err } },
// }

function pivot(rows, problem_index) {
    const usersMap = {};		// user -> { user, name, utac }
    const cells = {};		// user -> topic -> prob -> summary

    for (const row of rows) {
	const { user, name, student_id, utac, topic, prob, html, cell_type, lang, cmd, status } = row;
	if (!usersMap[user]) usersMap[user] = { user, name, student_id, utac };
	if (!cells[user])              cells[user] = {};
	if (!cells[user][topic])       cells[user][topic] = {};
	if (!cells[user][topic][prob]) {
	    cells[user][topic][prob] = {
		// the number of times hey is called
		hey: 0,
		// for each language
		//   w : number of writefile cells
		//   c : { 0: count of compile cells with status 0, 1: count of compile cells with status != 0 }
		//   r : { 0: count of run cells with status 0, 1: count of run cells with status != 0 }
		//   "?": catch-all for unknown commands (neither compile nor run)
		// "?": catch-all for unknown languages
		go:  { w: 0, c: { 0: 0, 1: 0 }, r: { 0: 0, 1: 0 }, "?": { 0: 0, 1: 0 } },
		jl:  { w: 0, c: { 0: 0, 1: 0 }, r: { 0: 0, 1: 0 }, "?": { 0: 0, 1: 0 } },
		ml:  { w: 0, c: { 0: 0, 1: 0 }, r: { 0: 0, 1: 0 }, "?": { 0: 0, 1: 0 } },
		rs:  { w: 0, c: { 0: 0, 1: 0 }, r: { 0: 0, 1: 0 }, "?": { 0: 0, 1: 0 } },
		"?": { w: 0, c: { 0: 0, 1: 0 }, r: { 0: 0, 1: 0 }, "?": { 0: 0, 1: 0 } },
		// link to detailed logs
		html: html,
	    };
	}
	const s = cells[user][topic][prob];

	if (cell_type === 'hey') {
	    s.hey += 1;
	} else if (cell_type === 'writefile') {
	    s[lang].w += 1;
	} else if (cell_type === 'bash') {
	    console.assert(status !== "", "Expected non-empty status for bash cell");
	    const st = status ? 0 : 1;
	    const cm = cmd === 'compile' ? 'c' : cmd === 'run' ? 'r' : '?';
	    s[lang][cm][st] += 1;
	}
    }
    const users = Object.values(usersMap).sort((a, b) => a.user.localeCompare(b.user));
    return { users, cells }
}


// -- Step 2: make a summary of each (topic, prob), aggregating over users, per problem) --------------

function accum(s, r) {
    // s: summary for one user/topic/prob
    // r: aggregate summary for one topic/prob (over users) or one user (over topic/probs)
    r.n += 1;
    r.hey += s.hey;
    for (const lang of ["go", "jl", "ml", "rs", "?"]) {
	const ri = r[lang];
	const si = s[lang];
	ri.w += si.w;
	for (const cmd of ["c", "r", "?"]) {
	    ri[cmd].n += (si[cmd][0] + si[cmd][1]) > 0 ? 1 : 0;
	    ri[cmd][0] += si[cmd][0] > 0 ? 1 : 0;
	    ri[cmd][1] += si[cmd][1];
	}
	for (const cmd of ["c", "r", "?"]) {
	    if (ri[cmd].n > 0) {
		ri[cmd][1] /= ri[cmd].n;
	    } else {
		console.assert(ri[cmd][1] == 0);
	    }
	}
    }
}

function summarizeTopicProb(topics_probs, users, cells) {
    // users : [{ user, name, utac }, ...]
    // topics_probs : [[topic, [prob, prob, ...]], [topic, [prob, prob, ...]], ...]
    const result = {};
    for (const [ topic, probs ] of topics_probs) {
	if (!result[topic]) result[topic] = {};
	for (const prob of probs) {
	    if (!result[topic][prob]) result[topic][prob] = {
		// number of topic/probs with at least one activity (hey, write, compile, or run)
		n: 0,
		// avg number of heys per user
		hey: 0,
		// w : avg number of writefile cells per user
		// c : { n: number of users with at least one compile,
		//       0: number of users with at least one compile cell with status 0,
		//       1: avg number of compile cells with status != 0 per user }
		// r : { n: number of users with at least one compile,
		//       0: number of users with at least one run cell with status 0,
		//       1: avg number of run cells with status != 0 per user }
		// "?": catch-all for unknown commands (neither compile nor run)
		go:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
		jl:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
		ml:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
		rs:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
		"?": { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
	    };
	    const r = result[topic][prob];
	    for (const { user, name, utac } of users) {
		const s = cells[user]?.[topic]?.[prob];
		if (!s) continue;
		accum(s, r);
	    }
	    if (r.n > 0) {
		r.hey /= r.n;
	    }
	}
    }
    return result;
}

// -- Step 3: row summaries (aggregate over problems, per user) -----------------

function summarizeUser(users, topics_probs, cells) {
    const result = {};
    for (const { user, name, utac } of users) {
	if (!result[user]) result[user] = {
	    // number of topic/probs with at least one activity (hey, write, compile, or run)
	    n: 0,
	    // avg number of heys
	    hey: 0,
	    // w : avg number of writefile cells per user
	    // c : { n: number of topic/probs with at least one compile,
	    //       0: number of topic/probs with at least one compile cell with status 0,
	    //       1: avg number of compile cells with status != 0 per topic/prob }
	    // r : { n: number of topic/probs with at least one compile,
	    //       0: number of topic/probs with at least one run cell with status 0,
	    //       1: avg number of run cells with status != 0 per topic/prob }
	    // "?": catch-all for unknown commands (neither compile nor run)
	    go:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
	    jl:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
	    ml:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
	    rs:  { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
	    "?": { w: 0, c: { n: 0, 0: 0, 1: 0 }, r: { n: 0, 0: 0, 1: 0 }, "?": { n: 0, 0: 0, 1: 0 } },
	};
	const r = result[user];
	for (const [topic, probs] of topics_probs) {
	    for (const prob of probs) {
		const s = cells[user]?.[topic]?.[prob];
		if (!s) continue;
		accum(s, r);
	    }
	}
	if (r.n > 0) {
	    r.hey /= r.n;
	}
    }
    return result;
}

// -- Step 4: render ------------------------------------------------------------

function render({ users, problem_index, topicProbSummary, userSummary, cells }) {
    const wrap  = document.getElementById('tableWrap');
    const table = document.createElement('table');
    table.className = 'outer';

    // // Group columns by topic for the two-row header
    // const topicGroups = [];
    // for (const { topic, prob } of columns) {
    // 	const last = topicGroups[topicGroups.length - 1];
    // 	if (last && last.topic === topic) last.probs.push(prob);
    // 	else topicGroups.push({ topic, probs: [prob] });
    // }

    // USER | SUMMARY |    TOPIC0     |    TOPIC1     | ...
    //                | prob0 | prob1 | prob0 | prob1 | ...

    // Header row 1: topic groups + Summary column
    const thead    = table.createTHead();
    const topicRow = thead.insertRow();
    topicRow.className = 'topic-row';

    // 'User' corner cell
    const cornerTop = document.createElement('th');
    cornerTop.rowSpan = 2;
    cornerTop.textContent = 'User';
    topicRow.appendChild(cornerTop);

    // 'Summary' cell
    const thSum = document.createElement('th');
    thSum.rowSpan = 2;
    thSum.textContent = 'Summary';
    topicRow.appendChild(thSum);

    // topic row
    for (const [ topic, probs ] of problem_index) {
	const th = document.createElement('th');
	th.colSpan = probs.length;
	th.textContent = topic;
	topicRow.appendChild(th);
    }

    // Header row 2: individual problem names
    const probRow = thead.insertRow();
    probRow.className = 'prob-row';
    for (const [ topic, probs ] of problem_index) {
	for (const prob of probs) {
	    const th = document.createElement('th');
	    th.textContent = prob;
	    probRow.appendChild(th);
	}
    }

    // Body: one row per user
    const tbody = table.createTBody();

    // Top row: column summaries
    const sumTr = tbody.insertRow();
    sumTr.className = 'summary-row';

    const sumUserTd = sumTr.insertCell();
    sumUserTd.className = 'user-cell';
    sumUserTd.innerHTML = '<div class="user-name">Summary</div>';

    // Top-left corner: empty
    const cornerTd = sumTr.insertCell();
    cornerTd.className = 'act-cell empty';

    for (const [ topic, probs ] of problem_index) {
	for (const prob of probs) {
	    const td = sumTr.insertCell();
	    td.className = 'act-cell';
	    const s = topicProbSummary[topic]?.[prob];
	    if (!s || s.n === 0) { td.classList.add('empty'); continue; }
	    td.appendChild(buildSummaryTable(s));
	}
    }

    for (const { user, name, student_id, utac } of users) {
	const tr = tbody.insertRow();

	const userTd = tr.insertCell();
	userTd.className = 'user-cell';
	userTd.innerHTML = `
      <div class="user-name">${escHtml(name)}</div>
      <div class="user-id">${escHtml(user)}</div>
      <div class="user-sid">${escHtml(student_id ?? '')}</div>
      <div class="user-utac">${escHtml(utac)}</div>`;

	// Row summary cell
	const rsTd = tr.insertCell();
	rsTd.className = 'act-cell';
	const s = userSummary[user];
	if (!s || s.n === 0) rsTd.classList.add('empty');
	else rsTd.appendChild(buildSummaryTable(s));

	for (const [ topic, probs ] of problem_index) {
	    for (const prob of probs) {
		const td = tr.insertCell();
		td.className = 'act-cell';
		const s = cells[user]?.[topic]?.[prob];
		if (!s) { td.classList.add('empty'); continue; }
		td.appendChild(buildInnerTable(s));
		td.appendChild(buildHref(s));
	    }
	}
    }
    wrap.appendChild(table);

    // freeze the topic-row and prob-row
    const headerRows = table.querySelectorAll('tr.topic-row, tr.prob-row');
    let top = 0;
    for (const row of headerRows) {
	for (const th of row.querySelectorAll('th')) {
	    th.style.top = top + 'px';
	}
	top += row.offsetHeight;
    }
}

function buildHref(s) {
    const a = document.createElement('a');
    a.href = s.html;
    a.target = '_blank';
    a.textContent = 'log';
    a.className = 'cell-link';
    return a;
}

// -- Inner table for one (user, topic/prob) cell -------------------------------
//
//         write  c/0  c/1  r/0  r/1
//   go
//   rs
//   hey

function buildInnerTable(s) {
    const t = document.createElement('table');
    t.className = 'inner';

    // if (s.hey === 0) return t;
    appendInnerHeader(t, ['', 'w', 'cEr', 'cOK', 'rEr', 'rOK']);
    const tbody = t.createTBody();
    for (const lang of ["go", "jl", "ml", "rs"]) {
	const tr = tbody.insertRow();
	cell(tr, lang, 'label');
	si = s[lang];
	cell(tr, si.w);
	cell(tr, si.c[1]);
	cell(tr, si.c[0]);
	cell(tr, si.r[1]);
	cell(tr, si.r[0]);
    }
    const tr = tbody.insertRow();
    tr.className = 'row-hey';
    cell(tr, 'hey');
    cell(tr, s.hey);
    for (let i = 0; i < 4; i++) cell(tr, '');

    return t;
}

// -- Summary table for row/column summary cells --------------------------------
//
//         wrote  compiled  ce/N  cOk  ran  re/N  rOk
//   go
//   rs
//   hey    (avg hey per problem or per user)

function buildSummaryTable(s) {
    const t = document.createElement('table');
    t.className = 'inner';

    //appendInnerHeader(t, ['', 'w', 'c', 'cEr', 'cOk', 'r', 'rEr', 'rOk']);
    appendInnerHeader(t, ['', 'w', 'cEr', 'cOk', 'rEr', 'rOk']);
    const tbody = t.createTBody();
    for (const lang of ["go", "jl", "ml", "rs"]) {
	const si = s[lang];
	const tr = tbody.insertRow();
	cell(tr, lang, 'label');
	cell(tr, si.w);
	//cell(tr, si.c.n);
	cell(tr, si.c[1] > 0 ? si.c[1].toFixed(2) : si.c[1]);
	cell(tr, si.c[0]);
	//cell(tr, si.r.n);
	cell(tr, si.r[1] > 0 ? si.r[1].toFixed(2) : si.r[1]);;
	cell(tr, si.r[0]);
    }
    const tr = tbody.insertRow();
    tr.className = 'row-hey';
    cell(tr, 'hey', 'label');
    cell(tr, s.hey > 0 ? s.hey.toFixed(2) : s.hey);
    for (let i = 0; i < 4; i++) cell(tr, '');

    return t;
}

// -- DOM helpers ---------------------------------------------------------------

function appendInnerHeader(table, cols) {
    const thead = table.createTHead();
    const hr    = thead.insertRow();
    for (const col of cols) {
	const th = document.createElement('th');
	th.textContent = col;
	hr.appendChild(th);
    }
}

function cell(tr, text, cls) {
    const td = tr.insertCell();
    td.textContent = (text === 0 || text === '0') ? '' : text;
    if (cls) td.className = cls;
    return td;
}

function escHtml(str) {
    return String(str)
	.replace(/&/g, '&amp;')
	.replace(/</g, '&lt;')
	.replace(/>/g, '&gt;')
	.replace(/"/g, '&quot;');
}

function main() {
    // Placeholder until data is embedded
    const { users, cells } = pivot(DATA);
    const topicProbSummary = summarizeTopicProb(PROBLEM_INDEX, users, cells);
    const userSummary = summarizeUser(users, PROBLEM_INDEX, cells);
    // { users, problem_index, topicProbSummary, userSummary, cells }
    render({ users, problem_index: PROBLEM_INDEX, topicProbSummary, userSummary, cells });
}
    
