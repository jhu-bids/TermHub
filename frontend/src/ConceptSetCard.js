import * as React from 'react';
import { styled } from '@mui/material/styles';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
// import CardActions from '@mui/material/CardActions';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import {get, } from 'lodash';
// import Button from '@mui/material/Button';
import {backend_url} from './App';

const bull = (
  <Box component="span" sx={{ display: 'inline-block', mx: '2px', transform: 'scale(0.8)' }} >•</Box>
);

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

export default function ConceptSetCards(props) {
  const {codeset_ids=[], cset_data={}} = props;
  const {selected_csets=[], } = cset_data;
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
                     codeset_id={cset.codeset_id}
                     key={cset.codeset_id}
                     cset={cset}
                     // widestConceptName={widestConceptName}
                     cols={Math.min(4, codeset_ids.length)}/>

          })
        }
      </div>;
}
function ConceptSetCard(props) {
  const [expanded, setExpanded] = React.useState(false);

  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  let {codeset_id, cset, cols, widestConceptName,} = props;
  // switch to using data from cset_data -- passed down props:
  const {codeset_ids = [], cset_data = {}} = props;

  let tags = [];
  let display_props = {}
  display_props['Code set ID'] = cset.codeset_id;
  display_props['Concepts'] = cset.concepts;
  display_props['Patient count'] = '~ ' + cset.approx_distinct_person_count.toLocaleString();
  display_props['Record count'] = '~ ' + cset.approx_total_record_count.toLocaleString();

  if (cset.is_most_recent_version) {
    tags.push('Most recent version');
  }

  let intention = [];
  if (cset.intention_container) {
    intention.push('Container: ' + cset.intention_container);
  }
  if (cset.intention_version) {
    intention.push('Version: ' + cset.intention_version);
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
  let researcherContent = '';
  if ((cset.researchers||[]).length) {
    const r = Object.entries(cset.researchers).map(e => {
      const type = e[0];
      const name = get(e[1], 'properties.name', 'huh?');
      return (
          <Typography variant="body2" color="text.secondary" key={type} sx={{overflow: 'clip',}}>
            <strong>{type}</strong>: {name}
          </Typography>
      )
    });
    return  <div>
              <Typography variant="h6" color="text.primary" gutterBottom>
                Contributors
              </Typography>
              {r}
            </div>
  }
  // display_props['props not included yet'] = 'status_version, status_container, stage, concept count';
  return (
      <Box sx={{ minWidth: 275, margin: '8px',  }}>
        <Card variant="outlined" sx={{maxWidth: 345}}>
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
            <Typography variant="h6" color="text.primary" gutterBottom>
              {cset.concept_set_version_title}
            </Typography>
            <Typography color="text.primary" gutterBottom>
              {tags.join(', ')}
            </Typography>
            {
              Object.keys(display_props).map(pkey => (
                  <Typography variant="body2" color="text.secondary" key={pkey} sx={{overflow: 'clip',}}>
                    <strong>{pkey}</strong>: {display_props[pkey]}
                  </Typography>
              ))
            }
            { researcherContent }

            <Typography color="text.primary" gutterBottom>
              <a href={`https://unite.nih.gov/workspace/hubble/objects/${cset.rid}`} target="_blank">Open in Enclave</a>
            </Typography>
            <Typography color="text.primary" gutterBottom>
              <a href={backend_url(`cset-download?codeset_id=${cset.codeset_id}`)} target="_blank">Export JSON</a>
            </Typography>
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
      </Box>
  );
}


