import React from 'react';

const pct_fmt = num => Number(num).toLocaleString(undefined,{style: 'percent', minimumFractionDigits:2});
const fmt = num => Number(num).toLocaleString();

function StatsMessage(props) {
  const {codeset_ids=[], all_csets=[], cset_data={}} = props;
  const {related_csets=[], concepts } = cset_data;

  return <p style={{margin:0, fontSize: 'small',}}>The <strong>{codeset_ids.length} concept sets </strong>
    selected contain <strong>{(concepts||[]).length} distinct concepts</strong>.
    The following <strong>{related_csets.length} concept sets </strong>
    ({ pct_fmt(related_csets.length / all_csets.length) })
    have 1 or more concepts in common with the selected sets. Select from
    below if you want to add to the above list.</p>
}

export {pct_fmt, fmt, StatsMessage, };
