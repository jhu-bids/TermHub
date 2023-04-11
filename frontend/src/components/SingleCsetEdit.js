import * as React from "react";
import { NavLink } from "react-router-dom";
import { ConceptSetCard } from "./components/ConceptSetCard";

function SingleCsetEdit(props) {
  const { edit_codeset_id, cset_data = {}, prev } = props;
  const { selected_csets = [], researchers = {} } = cset_data;
  console.log(props);
  if (selected_csets.length !== 1) {
    return (
      <h3>Error: expected 1 selected_cset, got {selected_csets.length}</h3>
    );
  }
  const cset = selected_csets[0];
  return (
    <div>
      <NavLink
        // component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
        to={decodeURIComponent(prev)}
        sx={{ my: 2, color: "white", display: "block" }}
      >
        Return to previous page
      </NavLink>
      <pre>{JSON.stringify(Object.keys(props), null, 2)}</pre>
      edit: {edit_codeset_id}
      <ConceptSetCard
        {...props}
        key={cset.codeset_id}
        cset={cset}
        researchers={researchers}
        // widestConceptName={widestConceptName} cols={Math.min(4, codeset_ids.length)}
      />
    </div>
  );
}

export { SingleCsetEdit };
