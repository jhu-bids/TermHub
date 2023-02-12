import TranslateIcon from '@mui/icons-material/Translate';
import BlockIcon from '@mui/icons-material/Block';
import { Add, } from '@mui/icons-material';
// import {SvgIcon} from "@mui/material";
import Box from '@mui/material/Box';
// import Typography from '@mui/material/Typography';
import {isEmpty, get, } from 'lodash'; // set, map, omit, pick, uniq, reduce, cloneDeepWith, isEqual, uniqWith, groupBy,
import IconButton from '@mui/material/IconButton';
// import {ComparisonDataTable} from './ComparisonDataTable';
import {Tooltip} from './Tooltip';
import {searchParamsToObj, updateSearchParams, } from "./utils";

function getEditCodesetFunc(props) {
  const {searchParams, } = props;
  return (evt) => {
    let ec = parseInt(evt.target.getAttribute('codeset_id'));
    let sp = searchParamsToObj(searchParams);
    if (sp.editCodesetId === ec) {
      updateSearchParams({...props, delProps: ['editCodesetId']});
    } else {
      updateSearchParams({...props, addProps: {editCodesetId: ec}});
    }
  }
}

function getCodesetEditState({csetEditState, codeset_id}) {
  return csetEditState[codeset_id] || {
    Add: {},
    Remove: [],
    Update: {}
  };
}
function getCodesetEditActionFunc({searchParams, setSearchParams}) {
  return (props) => {
    const {codeset_id, concept_id, action, item, flag, } = props;
    let sp = searchParamsToObj(searchParams);
    let {csetEditState={}, } = sp;
    let csidState = getCodesetEditState({csetEditState, codeset_id});
    if (get(csetEditState, [codeset_id, concept_id])) {
      // i don't know what this block of code is for
      throw new Error("what's happening here?")
      console.log("is this block getting called?")
      delete csetEditState[codeset_id][concept_id];
      if (isEmpty(csetEditState[codeset_id])) {
        delete csetEditState[codeset_id];
      }
    }
    if (action === 'Add') {
      let item = { codeset_id, concept_id, csm: false, item: true, status: 'Addition'};
      Object.keys(FLAGS).forEach(flag => {item[flag] = false});
      csidState.Add[concept_id] = item;
      csetEditState[codeset_id] = csidState;
      updateSearchParams({...props, addProps: {csetEditState}});
      return;
    }
    if (action === 'Remove') {
      let removeList = new Set([...csidState[codeset_id].Remove, concept_id]); // don't allow dups
      csidState.Remove = [...removeList];
      csetEditState[codeset_id] = csidState;
      updateSearchParams({...props, addProps: {csetEditState}});
      return;
    }
    if (action === 'Update') {
      throw new Error('not finished yet');
      item[flag] = !item[flag];
      csidState.Update[concept_id] = item;
      csetEditState[codeset_id] = csidState;
      updateSearchParams({...props, addProps: {csetEditState}});
      return;
    }
    throw new Error("what's happening here?")
  }
}

function EditInfo(props) {
  const {editCodesetId, csetEditState, } = props;
  return (
      <Box sx={{ p: 2, border: '1px dashed grey' }}>
        <pre>{JSON.stringify(csetEditState/*[editCodesetId]*/, null, 2)}</pre>
        {
          /*
            Object.values(csetEditState[editCodesetId]).map(
              (item) => {
                return (
                    <Typography key={item.concept_id} >
                      { state ? 'Adding' : 'Removing' } {conceptLookup[concept_id].concept_name}
                    </Typography>
                )
              }
          )
          */
        }
      </Box>
  );
}

const FLAGS = {
  // includeMapped: {component: TranslateIcon, sz:12, tt: 'Include Mapped'},
  // includeDescendants: {component: TreeIcon, sz:12, tt: 'Include descendants'},
  // isExcluded: {component: BlockIcon, sz:12, tt: 'Exclude'},
  includeMapped:      {symbol: 'M', tt: 'Include Mapped'},
  includeDescendants: {symbol: 'D', tt: 'Include descendants'},
  isExcluded:         {symbol: 'X', tt: 'Exclude'},
}
function OptionIcon(props) {
  const {editAction, item, flag, } = props;
  const on = !!item[flag];
  const icon = FLAGS[flag];
  // const OptIcon = icon.component;
  return (
    <Tooltip label={icon.tt + ' =' + (on ? 'True' : 'False')}>
      <IconButton
        onClick={()=>editAction({...props, item, flag, action: 'Update'})}
        size='9px'
        // color={on ? 'primary' : 'secondary'}
        sx={{ // width:icon.sz+'px', height:icon.sz+'px',
          fontWeight: on ? 'bolder' : 'regular',
          fontSize: '.7rem',
          margin: '0px 2px 2px 2px',
          // margin: '0px',
          padding: '0px',
          opacity: on ? 1 : .6,
          // backgroundColor: on ? 'lightblue' : '',
          // border: on ? '1px solid white' : '',
          // border: '2px solid white',
        }}
      >
        {icon.symbol}
      </IconButton>
    </Tooltip>
  );
}
function getItem({codeset_id, concept_id, cset_data: {csmiLookup}, csetEditState, }) {
  const item = {...csmiLookup[codeset_id][concept_id]};
  if (isEmpty(item)) {
    const new_item = get(csetEditState, [codeset_id, 'Add', concept_id]);
    return new_item;
  }
  const delete_item = get(csetEditState, [codeset_id, 'Add', concept_id]);
  if (delete_item) {
    return {...delete_item, status: 'Deletion'};
  }
  return item;
}
function cellStatus(props) {
  const {cset_col:{codeset_id}, row:{concept_id},
          editCodesetId, cset_data, csetEditState, } = props;
  const item = getItem({
                         codeset_id, concept_id, cset_data, csetEditState, });
  const editing = editCodesetId === codeset_id;
  let edit = (item||{}).status;
  const editState = getCodesetEditState({csetEditState, codeset_id});

  if (editing) {
    if (editCodesetId in editState.Add) {
      if (edit !== 'Addition') {
        throw new Error('problem with item status');
      }
    }
    if (editCodesetId in editState.Update) {
      if (edit) {
        throw new Error("concept should only have one edit at a time")
      }
      if (edit !== 'Update') {
        throw new Error('problem with item status');
      }
    }
    if (editState.Remove.includes(editCodesetId)) {
      if (edit) {
        throw new Error("concept should only have one edit at a time")
      }
      if (edit !== 'Deletion') {
        throw new Error('problem with item status');
      }
    }
  }
  return {editing, edit, item, };
}
function cellStyle(props) {
  const {editing, edit, item} = cellStatus(props);
  let style = {};
  if (!item) {
    return style;  // no styling
  }
  if (item.csm && item.item) { style.backgroundColor = 'orange' }
  else if (item.csm ) { style.backgroundColor = 'lightgray' }
  else if (item.item ) { style.backgroundColor = 'plum' }
  if (editing) {
    if (edit === 'Addition') { style.backgroundColor = 'lightgreen' }
    else if (edit === 'Deletion') { style.backgroundColor = 'pink' }
    else if (edit === 'Update') { style.backgroundColor = 'lightblue' }
  }
  return style;
}

function ItemOptions(props) {
  let {item, editing, editAction, } = props;
  let flags, removeItem, action;
  if (editing) {
    flags = Object.keys(FLAGS);
    action = 'Remove';
    if (item.status) {
      action = `Cancel ${item.status}`;
      if (item.status === 'Deletion') {
        return <Tooltip label={action}>Deleted</Tooltip>;
      }
    }
    removeItem =
        <Tooltip label={action}>
          <BlockIcon
              onClick={()=>editAction({...props, item, action})}
              sx={{
                width:'12px',
                height:'12px',
                margin: '2px 2px 0px 2px',
                padding: '0px',
              }}
          />
        </Tooltip>;
  } else {
    flags = Object.keys(FLAGS).filter(key => item[key])
  }
  const cellStuff = (
      <span>
        {removeItem}
        { flags.map((flag,i) => {
              return <OptionIcon {...props} item={item} flag={flag} key={flag} />
            })
        }
      </span>
  );
  return cellStuff;
}
/*
trying to figure out what to display to convey relationships between expression items and descendants and other
related concepts -- mapped and excluded
 */
function CellCheckbox(props) {
  const {cset_col:{codeset_id}, row:{concept_id}, editCodesetId, editAction, } = props;
  const item = getItem({...props, codeset_id, concept_id,})

  // should get from csetEditState and, if not there, then csmiLookup

  let checked, contents;
  checked = !! item;

  if (editCodesetId && codeset_id === editCodesetId) {
    if (!item || !item.item) {
      contents = <Add onClick={()=>editAction({...props, codeset_id, concept_id, action: 'Add'})}/>
    } else {
      return <ItemOptions {...props} item={item} editing={true}/>;
    }
    /*
    if (concept_id in csetEditState) { // should be keyed by codeset_id,concept_id, right?
        checked = ! checked;
    }
    contents = <Checkbox checked={checked} onChange={editAction(codeset_id, concept_id)}/>
     */
  } else {
    contents = <span>{checked ? '\u2713' : ''}</span>;
  }
  if (item) {
    return <ItemOptions {...props} item={item}/>;
    // return  <Tooltip label={<pre>{JSON.stringify(item, null, 2)}</pre>} placement="bottom">{contents}</Tooltip>
  } else {
    return contents
  }
}

export {EditInfo, getCodesetEditActionFunc, getEditCodesetFunc, CellCheckbox, cellStyle, }

/*
function TreeIcon(props) {
  return (
      <SvgIcon {...props} /* viewBox="90 120 510 300" * / viewBox="0 0 24 24" >
        <path xmlns="http://www.w3.org/2000/svg" d="m 20.8125 12.875 c -0.3164 0 -0.6156 0.0709 -0.8877 0.192 l -1.8901 -2.6461 c 0.3631 -0.39 0.5903 -0.9094 0.5903 -1.4834 c 0 -1.2063 -0.9813 -2.1875 -2.1875 -2.1875 c -0.3168 0 -0.6156 0.0709 -0.8877 0.1926 l -1.8901 -2.6461 c 0.3631 -0.3906 0.5903 -0.91 0.5903 -1.484 c 0 -1.2063 -0.9813 -2.1875 -2.1875 -2.1875 s -2.1875 0.9813 -2.1875 2.1875 c 0 0.574 0.2272 1.0934 0.5903 1.484 l -1.8901 2.6461 c -0.2721 -0.1217 -0.5709 -0.1926 -0.8877 -0.1926 c -1.2063 0 -2.1875 0.9813 -2.1875 2.1875 c 0 0.5744 0.2272 1.0938 0.591 1.485 l -1.8904 2.6451 c -0.2721 -0.1217 -0.5713 -0.1926 -0.8881 -0.1926 c -1.2063 0 -2.1875 0.9813 -2.1875 2.1875 s 0.9813 2.1875 2.1875 2.1875 s 2.1875 -0.9813 2.1875 -2.1875 c 0 -0.574 -0.2272 -1.093 -0.5899 -1.4836 l 1.8908 -2.6455 c 0.2715 0.1211 0.5701 0.1916 0.8865 0.1916 s 0.6156 -0.0709 0.8873 -0.192 l 1.8901 2.6461 c -0.3627 0.3904 -0.5899 0.9094 -0.5899 1.4834 s 0.2272 1.0934 0.5903 1.484 l -1.8901 2.6461 c -0.2721 -0.1217 -0.5709 -0.1926 -0.8877 -0.1926 c -1.2063 0 -2.1875 0.9813 -2.1875 2.1875 s 0.9813 2.1875 2.1875 2.1875 s 2.1875 -0.9813 2.1875 -2.1875 c 0 -0.574 -0.2272 -1.0934 -0.5903 -1.484 l 1.8901 -2.6461 c 0.2717 0.1217 0.5709 0.1926 0.8877 0.1926 c 0.3164 0 0.6156 -0.0709 0.8877 -0.192 l 1.8897 2.6465 c -0.3633 0.3906 -0.5899 0.9094 -0.5899 1.483 c 0 1.2063 0.9813 2.1875 2.1875 2.1875 s 2.1875 -0.9813 2.1875 -2.1875 s -0.9813 -2.1875 -2.1875 -2.1875 c -0.3168 0 -0.6164 0.0709 -0.8885 0.193 l -1.8891 -2.6465 c 0.3629 -0.3906 0.5901 -0.91 0.5901 -1.484 c 0 -1.2063 -0.9813 -2.1875 -2.1875 -2.1875 c -0.3168 0 -0.616 0.0709 -0.8881 0.1926 l -1.8897 -2.6461 c 0.3631 -0.3902 0.5903 -0.9095 0.5903 -1.484 c 0 -0.574 -0.2272 -1.0934 -0.5903 -1.484 l 1.8901 -2.6461 c 0.2717 0.1217 0.5709 0.1926 0.8877 0.1926 s 0.6156 -0.0709 0.8877 -0.1926 l 1.8901 2.6461 c -0.3631 0.3906 -0.5903 0.91 -0.5903 1.484 c 0 1.2063 0.9813 2.1875 2.1875 2.1875 c 0.3168 0 0.6156 -0.0709 0.8877 -0.1926 l 1.8901 2.6455 c -0.3631 0.3912 -0.5903 0.9105 -0.5903 1.4846 c 0 1.2063 0.9813 2.1875 2.1875 2.1875 s 2.1875 -0.9813 2.1875 -2.1875 s -0.9813 -2.1875 -2.1875 -2.1875 z m -17.5 3.5 c -0.7237 0 -1.3125 -0.5888 -1.3125 -1.3125 s 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 s -0.5888 1.3125 -1.3125 1.3125 z m 3.0625 -7.4375 c 0 -0.7237 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 s -0.5888 1.3125 -1.3125 1.3125 s -1.3125 -0.5888 -1.3125 -1.3125 z m 1.3125 13.5625 c -0.7237 0 -1.3125 -0.5888 -1.3125 -1.3125 s 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 s -0.5888 1.3125 -1.3125 1.3125 z m 10.0625 -1.3125 c 0 0.7237 -0.5888 1.3125 -1.3125 1.3125 s -1.3125 -0.5888 -1.3125 -1.3125 s 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 z m -4.375 -6.125 c 0 0.7237 -0.5888 1.3125 -1.3125 1.3125 s -1.3125 -0.5888 -1.3125 -1.3125 s 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 z m -2.625 -12.25 c 0 -0.7237 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 s -0.5888 1.3125 -1.3125 1.3125 s -1.3125 -0.5888 -1.3125 -1.3125 z m 4.375 6.125 c 0 -0.7237 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 s -0.5888 1.3125 -1.3125 1.3125 s -1.3125 -0.5888 -1.3125 -1.3125 z m 5.6875 7.4375 c -0.7237 0 -1.3125 -0.5888 -1.3125 -1.3125 s 0.5888 -1.3125 1.3125 -1.3125 s 1.3125 0.5888 1.3125 1.3125 s -0.5888 1.3125 -1.3125 1.3125 z" fill="#000000"/>
        {/*<path xmlns="http://www.w3.org/2000/svg" d="m516.25 297.5c-6.3281 0-12.312 1.418-17.754 3.8398l-37.801-52.922c7.2617-7.8008 11.805-18.188 11.805-29.668 0-24.125-19.625-43.75-43.75-43.75-6.3359 0-12.312 1.418-17.754 3.8516l-37.801-52.922c7.2617-7.8125 11.805-18.199 11.805-29.68 0-24.125-19.625-43.75-43.75-43.75s-43.75 19.625-43.75 43.75c0 11.48 4.543 21.867 11.805 29.68l-37.801 52.922c-5.4414-2.4336-11.418-3.8516-17.754-3.8516-24.125 0-43.75 19.625-43.75 43.75 0 11.488 4.543 21.875 11.82 29.699l-37.809 52.902c-5.4414-2.4336-11.426-3.8516-17.762-3.8516-24.125 0-43.75 19.625-43.75 43.75s19.625 43.75 43.75 43.75 43.75-19.625 43.75-43.75c0-11.48-4.543-21.859-11.797-29.672l37.816-52.91c5.4297 2.4219 11.402 3.832 17.73 3.832s12.312-1.418 17.746-3.8398l37.801 52.922c-7.2539 7.8086-11.797 18.188-11.797 29.668s4.543 21.867 11.805 29.68l-37.801 52.922c-5.4414-2.4336-11.418-3.8516-17.754-3.8516-24.125 0-43.75 19.625-43.75 43.75s19.625 43.75 43.75 43.75 43.75-19.625 43.75-43.75c0-11.48-4.543-21.867-11.805-29.68l37.801-52.922c5.4336 2.4336 11.418 3.8516 17.754 3.8516 6.3281 0 12.312-1.418 17.754-3.8398l37.793 52.93c-7.2656 7.8125-11.797 18.188-11.797 29.66 0 24.125 19.625 43.75 43.75 43.75s43.75-19.625 43.75-43.75-19.625-43.75-43.75-43.75c-6.3359 0-12.328 1.418-17.77 3.8594l-37.781-52.93c7.2578-7.8125 11.801-18.199 11.801-29.68 0-24.125-19.625-43.75-43.75-43.75-6.3359 0-12.32 1.418-17.762 3.8516l-37.793-52.922c7.2617-7.8047 11.805-18.191 11.805-29.68 0-11.48-4.543-21.867-11.805-29.68l37.801-52.922c5.4336 2.4336 11.418 3.8516 17.754 3.8516s12.312-1.418 17.754-3.8516l37.801 52.922c-7.2617 7.8125-11.805 18.199-11.805 29.68 0 24.125 19.625 43.75 43.75 43.75 6.3359 0 12.312-1.418 17.754-3.8516l37.801 52.91c-7.2617 7.8242-11.805 18.211-11.805 29.691 0 24.125 19.625 43.75 43.75 43.75s43.75-19.625 43.75-43.75-19.625-43.75-43.75-43.75zm-350 70c-14.473 0-26.25-11.777-26.25-26.25s11.777-26.25 26.25-26.25 26.25 11.777 26.25 26.25-11.777 26.25-26.25 26.25zm61.25-148.75c0-14.473 11.777-26.25 26.25-26.25s26.25 11.777 26.25 26.25-11.777 26.25-26.25 26.25-26.25-11.777-26.25-26.25zm26.25 271.25c-14.473 0-26.25-11.777-26.25-26.25s11.777-26.25 26.25-26.25 26.25 11.777 26.25 26.25-11.777 26.25-26.25 26.25zm201.25-26.25c0 14.473-11.777 26.25-26.25 26.25s-26.25-11.777-26.25-26.25 11.777-26.25 26.25-26.25 26.25 11.777 26.25 26.25zm-87.5-122.5c0 14.473-11.777 26.25-26.25 26.25s-26.25-11.777-26.25-26.25 11.777-26.25 26.25-26.25 26.25 11.777 26.25 26.25zm-52.5-245c0-14.473 11.777-26.25 26.25-26.25s26.25 11.777 26.25 26.25-11.777 26.25-26.25 26.25-26.25-11.777-26.25-26.25zm87.5 122.5c0-14.473 11.777-26.25 26.25-26.25s26.25 11.777 26.25 26.25-11.777 26.25-26.25 26.25-26.25-11.777-26.25-26.25zm113.75 148.75c-14.473 0-26.25-11.777-26.25-26.25s11.777-26.25 26.25-26.25 26.25 11.777 26.25 26.25-11.777 26.25-26.25 26.25z"/>* /}
        {/*<path xmlns="http://www.w3.org/2000/svg" d="m548.24 403.2v-43.121h-96.316v-22.961h43.68v-109.2h-43.68v-43.121h-95.762v-22.961h47.039v-109.2h-109.76v109.76h47.039v22.398h-95.762v43.121h-47.039v109.76h47.039v22.961l-95.758-0.003906v42.559h-37.52v109.76h109.76v-109.76h-57.121v-28h176.4v28h-45.359v109.76h109.76l-0.003906-109.76h-48.719v-28h176.4v28h-57.121v109.76h109.76v-109.76zm-192.08-43.121h-96.32v-22.961h47.039v-109.2h-47.039v-28h176.4v28h-50.398v109.76h50.398v22.961l-80.082-0.003906z" />* /}
      </SvgIcon>
  );
}
*/