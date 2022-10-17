import * as React from 'react';
import { styled } from '@mui/material/styles';
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Card from '@mui/material/Card';
import CardHeader from '@mui/material/CardHeader';
import CardMedia from '@mui/material/CardMedia';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Collapse from '@mui/material/Collapse';
import Avatar from '@mui/material/Avatar';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import { red } from '@mui/material/colors';
import FavoriteIcon from '@mui/icons-material/Favorite';
import ShareIcon from '@mui/icons-material/Share';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import MoreVertIcon from '@mui/icons-material/MoreVert';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';

const bull = (
  <Box component="span" sx={{ display: 'inline-block', mx: '2px', transform: 'scale(0.8)' }} >•</Box>
);

const card = (
  <React.Fragment>
    <CardContent>
      <Typography sx={{ fontSize: 14 }} color="text.secondary" gutterBottom>
        Word of the Day
      </Typography>
      <Typography variant="h5" component="div">
        be{bull}nev{bull}o{bull}lent
      </Typography>
      <Typography sx={{ mb: 1.5 }} color="text.secondary">
        adjective
      </Typography>
      <Typography variant="body2">
        well meaning and kindly.
        <br />
        {'"a benevolent smile"'}
      </Typography>
    </CardContent>
    <CardActions>
      <Button size="small">Learn More</Button>
    </CardActions>
  </React.Fragment>
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

export default function ConceptSetCard(props) {
  const [expanded, setExpanded] = React.useState(false);

  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  let {codeset_id, cset, cols, widestConceptName,} = props;
  // switch to using data from cset_data -- passed down props:
  const {codeset_ids = [], cset_data = {}} = props;
  const {concept_set_members_i = [], all_csets = [],} = cset_data;

  let tags = [];
  let display_props = {}
  display_props['Code set ID'] = cset.codeset_id;
  display_props['Concepts'] = cset.concepts;

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
          </CardContent>
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
        </Card>
      </Box>
  );
}


