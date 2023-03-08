import * as React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import {NavLink, useLocation} from "react-router-dom";
import {backend_url} from './App';

/*
import { styled } from '@mui/material/styles';
import CardActions from '@mui/material/CardActions';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import {get, } from 'lodash';
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
  const {cset_data={}} = props;
  const {selected_csets=[], researchers={}} = cset_data;
  if (!selected_csets.length) {
    return <div></div>;
  }
  return <div style={{ display: 'flex', flexWrap: 'wrap', flexDirection: 'row', margin: '20px',
                      /* height: '90vh', alignItems: 'stretch', border: '1px solid green', width:'100%',
                        'flex-shrink': 0, flex: '0 0 100%', */ }}>
        {
          selected_csets.map(cset => {
            // let widestConceptName = max(Object.values(cset.concepts).map(d => d.concept_name.length))
            return <ConceptSetCard  {...props}
                     key={cset.codeset_id}
                     cset={cset}
                     researchers={researchers}
                     // widestConceptName={widestConceptName} cols={Math.min(4, codeset_ids.length)}
            />

          })
        }
      </div>;
}
function ConceptSetCard(props) {
  let {cset, researchers={}, editing=false, } = props;
  /*
  const [expanded, setExpanded] = React.useState(false);
  const handleExpandClick = () => {
    setExpanded(!expanded);
  };
  // switch to using data from cset_data -- passed down props:
  const {codeset_ids = [], cset_data = {}} = props;
   */
  let tags = [];
  let display_props = {}
  display_props['Code set ID'] = cset.codeset_id;
  display_props['Concepts'] = cset.concepts;
  // fix to:
  // format: row => fmt(parseInt(row.distinct_person_cnt)),
  display_props['Patient count'] = '~ ' + cset.distinct_person_cnt.toLocaleString();
  display_props['Record count'] = '~ ' + cset.total_cnt.toLocaleString();

  if (cset.is_most_recent_version) {
    tags.push('Most recent version');
  }

  let intention = [];
  if (cset.container_intention) {
    intention.push('Container: ' + cset.container_intention);
  }
  if (cset.codeset_intention) {
    intention.push('Version: ' + cset.codeset_intention);
  }
  if (intention.length) {
    display_props.Intention = intention.join('; ');
  }
  if (cset.update_message) {
    display_props['Update message'] = cset.update_message;
  }
  if (cset.archived) {
    tags.push('Archived');
  }
  if (cset.has_review) {
    tags.push('Has review');
  }
  if (cset.provenance) {
    display_props['Provenance'] = cset.provenance;
  }
  if (cset.limitations) {
    display_props['Limitations'] = cset.limitations;
  }
  if (cset.limitations) {
    display_props['Limitations'] = cset.limitations;
  }
  if (cset.issues) {
    display_props['Issues'] = cset.issues;
  }
  if (cset.authoritative_source) {
    display_props['Authoritative source'] = cset.authoritative_source;
  }
  if (cset.project_id) {
    display_props['Project ID'] = cset.project_id;
  }


  let _researchers = Object.entries(cset.researchers).map(
    ([id, roles]) => {
      let r = researchers[id];
      r.roles = roles;
      return r
    })
  const researcher_info = _researchers.map(r => {
    return (
        <Typography variant="body2" color="text.secondary" key={r.emailAddress} sx={{overflow: 'clip',}} gutterBottom>
          <strong>{r.roles.join(', ')}:</strong><br/>
          <a href={`mailto:${r.emailAddress}`}>{r.name}</a>,
          <a href={r.institutionsId} target="_blank" rel="noreferrer">{r.institution}</a>,
          <a href={`https://orcid.org/${r.orcidId}`} target="_blank" rel="noreferrer">ORCID</a>.
        </Typography>
    )
  });
  let researcherContent = (
    <div>
      <Typography /*variant="h6"*/ color="text.primary" >Contributors</Typography>
      {researcher_info}
    </div>);
  // display_props['props not included yet'] = 'codeset_status, container_status, stage, concept count';
  const {search, pathname} = useLocation();
  /*
  const editSingleLink = (
      <NavLink
          // component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
          to={`/SingleCsetEdit?codeset_ids=${cset.codeset_id}&prev=${encodeURIComponent(pathname)}${encodeURIComponent(search)}`}
          sx={{ my: 2, color: 'white', display: 'block' }}
      >Edit</NavLink>
      )
   */
  return (
      <Card variant="outlined">
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
          {/*<Typography variant="h6" color="text.primary" gutterBottom>*/}
          {/*  {editing ? 'Editing' : ''} {cset.concept_set_version_title} {editSingleLink}*/}
          {/*</Typography>*/}
          <Typography variant="body2" color="text.primary" gutterBottom>
            {tags.join(', ')}
          </Typography>
          {
            Object.keys(display_props).map(pkey => (
                <Typography variant="body2" color="text.secondary" key={pkey} sx={{overflow: 'clip',}}>
                  <strong>{pkey}</strong>: {display_props[pkey]}
                </Typography>
            ))
          }
          <Typography variant="body2" color="text.primary" >
            {/*This link opens the version */}
            {/*<a href={`https://unite.nih.gov/workspace/hubble/external/object/v0/omop-concept-set?codeset_id=${cset.codeset_id}`} target="_blank" rel="noreferrer">Open in Enclave</a*/}
            {/*This link opens the container */}
            <a href={`https://unite.nih.gov/workspace/hubble/objects/${cset.container_rid}`} target="_blank">Open in Enclave</a
            >, <a href={backend_url(`cset-download?codeset_id=${cset.codeset_id}`)} target="_blank" rel="noreferrer">Export JSON</a>
          </Typography>
          { researcherContent }
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

export {ConceptSetCard};


