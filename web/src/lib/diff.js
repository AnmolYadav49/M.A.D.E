// Minimal line-based LCS diff (context/added/removed), styled to match the
// Claude Design mockup's red/green code panel. Good enough for the short,
// LLM-generated scripts this app diffs — not meant as a general-purpose differ.

function lcsTable(a, b) {
  const n = a.length, m = b.length;
  const table = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }
  return table;
}

export function diffLines(before, after) {
  const a = (before || '').split('\n');
  const b = (after || '').split('\n');
  const table = lcsTable(a, b);
  const rows = [];
  let i = 0, j = 0, n = 1;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      rows.push({ n: n++, marker: '', text: a[i], kind: 'ctx' });
      i++; j++;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      rows.push({ n: n++, marker: '-', text: a[i], kind: 'del' });
      i++;
    } else {
      rows.push({ n: n++, marker: '+', text: b[j], kind: 'add' });
      j++;
    }
  }
  while (i < a.length) { rows.push({ n: n++, marker: '-', text: a[i], kind: 'del' }); i++; }
  while (j < b.length) { rows.push({ n: n++, marker: '+', text: b[j], kind: 'add' }); j++; }
  return rows;
}

export function plainLines(code) {
  return (code || '').split('\n').map((text, idx) => ({ n: idx + 1, marker: '', text, kind: 'ctx' }));
}
