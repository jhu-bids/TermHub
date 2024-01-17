import * as React from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import {List, ListItem} from "@mui/material";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Button from "@mui/material/Button";
import {NEW_CSET_ID, newCsetProvenance, } from "../state/AppState";
import {newCsetAtlasWidget, copyConceptsFromWidget} from "./NewCset";
import {SOURCE_APPLICATION, SOURCE_APPLICATION_VERSION} from "../env";
// import Box from '@mui/material/Box';
import { useLocation } from "react-router-dom";
import {backend_url} from "../state/DataGetter";

/*
import { styled } from '@mui/material/styles';
import CardActions from '@mui/material/CardActions';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Button from '@mui/material/Button';

const bull = ( <Box component="span" sx={{ display: 'inline-block', mx: '2px', transform: 'scale(0.8)' }} >•</Box> );

const ExpandMore = styled((props) => {
  const { expand, ...other } = props;
  return <IconButton {...other} />;
})(({ theme, expand }) => ({
  transform: !expand ? 'rotate(0deg)' : 'rotate(180deg)',
  marginLeft: 'auto',
  transition: theme.transitions.create('transform', {
    duration: theme.transitions.duration.shortest,
  }),
}));
 */

export default function ConceptSetCards(props) {
  const { selected_csets = [], researchers = {} } = props;
  if (!selected_csets.length) {
    return <div></div>;
  }
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        flexDirection: "row",
        margin: "20px",
        /* height: '90vh', alignItems: 'stretch', border: '1px solid green', width:'100%',
                        'flex-shrink': 0, flex: '0 0 100%', */
      }}
    >
      {selected_csets.map((cset) => {
        // let widestConceptName = max(Object.values(cset.concepts).map(d => d.concept_name.length))
        return (
          <ConceptSetCard
            {...props}
            key={cset.codeset_id}
            cset={cset}
            researchers={researchers}
            // widestConceptName={widestConceptName} cols={Math.min(4, codeset_ids.length)}
          />
        );
      })}
    </div>
  );
}
export function ConceptSetCard(props) {
  let { cset, researchers = {}, editing = false, closeFunc, hideTitle,
        selected_csets, csmi, newCsetDispatch, conceptLookup, styles = {}} = props;
  let atlasWidget = null;
  let copyConceptsWidget = null;
  /*
  const [expanded, setExpanded] = React.useState(false);
  const handleExpandClick = () => {
    setExpanded(!expanded);
  };
  // switch to using data from cset_data -- passed down props:
  const {codeset_ids = [], cset_data = {}} = props;
   */
  let tags = [];
  let display_props = {};
  let enclaveLink;
  // display_props["Code set ID"] = cset.codeset_id;
  let intention = [];
  // display_props["Code set ID"] = cset.codeset_id; // moved below in order to add data-testid
  if (cset.container_intention) {
    display_props["Container intention"] = cset.container_intention;
  }
  if (cset.codeset_intention) {
    display_props["Version intention"] = cset.codeset_intention;
  }
  if (cset.update_message) {
    display_props["Update message"] = cset.update_message;
  }
  if (cset.archived) {
    tags.push("Archived");
  }
  if (cset.has_review) {
    tags.push("Has review");
  }
  if (cset.limitations) {
    display_props["Limitations"] = cset.limitations;
  }
  if (cset.limitations) {
    display_props["Limitations"] = cset.limitations;
  }
  if (cset.issues) {
    display_props["Issues"] = cset.issues;
  }
  if (cset.authoritative_source) {
    display_props["Authoritative source"] = cset.authoritative_source;
  }
  if (cset.project_id) {
    display_props["Project ID"] = cset.project_id;
  }
  if (cset.codeset_id === NEW_CSET_ID) {
    // if new cset, concepts should be in props and available here.
    delete display_props["Code set ID"];
    atlasWidget = newCsetAtlasWidget(cset, conceptLookup);
    copyConceptsWidget = copyConceptsFromWidget(cset, selected_csets, csmi, newCsetDispatch);
    display_props["Provenance"] = newCsetProvenance(cset);
  } else {
    if (cset.provenance) {
      display_props["Provenance"] = cset.provenance;
    }

    // fix to:
    // format: row => fmt(parseInt(row.distinct_person_cnt)),
    display_props["Patient count"] = typeof(cset.distinct_person_cnt) === 'number'
        ? "~ " + cset.distinct_person_cnt.toLocaleString() : '';
    display_props["Record count"] = typeof(cset.total_cnt) === 'number'
        ? "~ " + cset.total_cnt.toLocaleString() : '';
    display_props["Record count from term usage"] = typeof(cset.total_cnt_from_term_usage) === 'number'
        ? "~ " + cset.total_cnt_from_term_usage.toLocaleString() : '';

    if (cset.is_most_recent_version) {
      tags.push("Most recent version");
    }

    display_props["Container created at"] = new Date(cset.container_created_at).toLocaleString();
    display_props["Version created at"] = new Date(cset.codeset_created_at).toLocaleString();
    enclaveLink = (
        <Typography variant="body2" color="text.primary">
          <a
            href={backend_url(`cset-download?codeset_id=${cset.codeset_id}`)}
            target="_blank"
            rel="noreferrer"
            >
            Export JSON
          </a>; Open in Enclave: <a
            href={`https://unite.nih.gov/workspace/hubble/objects/${cset.container_rid}`}
            target="_blank"
          >
            Container
          </a>, <a
            href={`https://unite.nih.gov/workspace/hubble/external/object/v0/omop-concept-set?codeset_id=${cset.codeset_id}`}
            target="_blank"
          >
          Version
          </a>
        </Typography>
    );
  }
  display_props["Concept counts"] = (
      <>
        {
          Object.entries(cset.counts || {}).map(([grp,cnt]) => (
              <span style={{display: 'block', paddingLeft: '12px'}} key={grp}><strong>{grp}</strong>: {cnt.toLocaleString()}</span>
          ))
        }
      </>
  );
  let _researchers = Object.entries(cset.researchers || {}).map(([id, roles]) => {
    let r = researchers[id];
    if (!r) {
      return;
    }
    r.roles = roles;
    return r;
  }).filter(d => d);
  const researcher_info = _researchers.map((r) => {
    return (
        <Typography
            variant="body2"
            color="text.secondary"
            key={r.emailAddress}
            sx={{ overflow: "clip" }}
            gutterBottom
        >
          <strong>{r.roles.join(", ")}:</strong>
          <br />
          <a href={`mailto:${r.emailAddress}`}>{r.name}</a>
          , <a
            href={r.institutionsId} target="_blank" rel="noreferrer">{r.institution} </a>
          , <a href={`https://orcid.org/${r.orcidId}`} target="_blank" rel="noreferrer" >ORCID</a>.
        </Typography>
    );
  });
  let researcherContent = researcher_info.length ?
      ( <div>
            <Typography /*variant="h6"*/ color="text.primary">
              Contributors
            </Typography>
            {researcher_info}
          </div>
      ) : '';
  return (
    <Card
      variant="outlined"
      sx={{ display: "inline-block",
            overflow: "scroll!important",
            ...styles,
        /*maxWidth: '400px'*/ }}
    >
      {/*
        <CardHeader
            action={
              <IconButton aria-label="settings">
                <MoreVertIcon/>
              </IconButton>
            }
            // subheader={tags.join(bull)} doesn't work like this, but might be nice
            sx={{paddingBottom: '5px',}}
        />
        */}
      <CardContent sx={{}}>
        {
          hideTitle ? null :
              <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
              >
                <Typography variant="h6" color="text.primary" gutterBottom>
                  {editing ? "Editing" : ""} {cset.concept_set_version_title}
                </Typography>
                {closeFunc ? (
                    <IconButton onClick={closeFunc}>
                      <CloseIcon />
                    </IconButton>
                ) : null}
              </div>
        }
        <Typography variant="body2" color="text.primary" gutterBottom>
          {tags.join(", ")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ overflow: "clip" }} >
          <strong>Codeset ID</strong>: <span data-testid={"codeset_id-" + cset.codeset_id }>{cset.codeset_id}</span>
        </Typography>
        {Object.keys(display_props).map((pkey) => (
            <Typography variant="body2" color="text.secondary" key={pkey} sx={{ overflow: "clip" }} >
              <strong>{pkey}</strong>: {display_props[pkey]}
            </Typography>
        ))}
        {researcherContent}
        {enclaveLink}
        {atlasWidget}
        {copyConceptsWidget}
      </CardContent>
      {/*
        <CardActions disableSpacing>
          <IconButton size="small" aria-label="add to favorites">
            <FavoriteIcon/>
          </IconButton>
          <IconButton size="small" aria-label="share">
            <ShareIcon/>
          </IconButton>
          <Button size="small">View in Enclave</Button>
          <ExpandMore
              expand={expanded}
              onClick={handleExpandClick}
              aria-expanded={expanded}
              aria-label="show more"
          >
            <ExpandMoreIcon/>
          </ExpandMore>
        </CardActions>
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <CardContent>
            <List style={{height: '40%', overflowX: 'clip', overflowY: 'scroll'}}>
              { // TODO: figure out height for list
                cset.concept_items.map((concept, i) => {
                  return <ListItem style={{
                    margin: '3px 3px 3px 3px',
                    background: '#dbdbdb',
                    borderRadius: '5px',
                    fontSize: '0.8em'
                  }} key={i}>
                    <Typography>
                      {concept.concept_id}: {concept.concept_name}
                    </Typography>
                  </ListItem>
                })}
            </List>
          </CardContent>
        </Collapse>
        */}
    </Card>
  );
}