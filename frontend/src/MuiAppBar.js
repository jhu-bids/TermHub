// from https://mui.com/material-ui/react-app-bar/#ResponsiveAppBar.js
import React, {useState, useEffect} from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Menu from '@mui/material/Menu';
import MenuIcon from '@mui/icons-material/Menu';
import Container from '@mui/material/Container';
import Avatar from '@mui/material/Avatar';
import Button from '@mui/material/Button';
// import {Tooltip} from './Tooltip';
import Tooltip from '@mui/material/Tooltip';
import MenuItem from '@mui/material/MenuItem';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import {NavLink, useLocation} from "react-router-dom";
import { cloneDeep, } from "lodash";


import { styled, useTheme } from '@mui/material/styles';
import Drawer from '@mui/material/Drawer';
import CssBaseline from '@mui/material/CssBaseline';
import List from '@mui/material/List';
import Divider from '@mui/material/Divider';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import InboxIcon from '@mui/icons-material/MoveToInbox';
import MailIcon from '@mui/icons-material/Mail';

const drawerWidth = 240;

const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    flexGrow: 1,
    padding: theme.spacing(3),
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    marginLeft: `-${drawerWidth}px`,
    ...(open && {
      transition: theme.transitions.create('margin', {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.enteringScreen,
      }),
      marginLeft: 0,
    }),
  }),
);

const AppBarForDrawer = styled(AppBar, {
  shouldForwardProp: (prop) => prop !== 'open',
})(({ theme, open }) => ({
  transition: theme.transitions.create(['margin', 'width'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  ...(open && {
    width: `calc(100% - ${drawerWidth}px)`,
    marginLeft: `${drawerWidth}px`,
    transition: theme.transitions.create(['margin', 'width'], {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
}));

const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(0, 1),
  // necessary for content to be below app bar
  ...theme.mixins.toolbar,
  justifyContent: 'flex-end',
}));

export default function PersistentDrawerLeft({children}) {
  /*
    thoughts about where this is going:
    content = {
      search: {
        name: 'search', componentName: 'CsetSearch',
        requiredProps: { appStateSlices: ['codeset_ids'], dataStateSlices: ['all_csets'], },
        showInMenu: () => true // always
        showAs: 'panel',
        defaultShowProps: {
          style: {position: 'absolute'},
          place: { x: 20, y: 20, width: (windowSize) => windowSize.width * .9, height: 400 }
          shown: true, // turn off when comparison is turned on (maybe other rules)
          collapsed: false,
          collapseProps: { width: ({name}) => (name.length + 2) + 'em', height: '2em', },
        },
        currentShowProps: { ... },
      },
      csetsDataTable: {
        name: 'csetsDataTable', componentName: 'CsetsDataTable',
        requiredProps: { appStateSlices: ['codeset_ids'], dataStateSlices: ['selected_csets', 'related_csets'], },
        showInMenu: () => ({codeset_ids}) => codeset_ids > 0,
        showAs: 'panel',
        defaultShowProps: {
          style: {position: 'absolute'}, // should be same size and below search
          place: { x: 20, y: 20, width: (windowSize) => windowSize.width * .9, height: 400 }
          shown: true, // after codeset_ids (or selected_csets) changes
          collapsed: false,
          collapseProps: { width: ({name}) => (name.length + 2) + 'em', height: '2em', },
        },
        currentShowProps: { ... },
      },
      conceptNavigation: { }, // doesn't exist yet (but may include search, tabular, graphical, ...)
      comparison: {
        name: 'csetComparison',
        componentName: 'CsetComparisonPage' // OR:
        subComponents: CsetComparisonTable + options and controls, legend
      },
      comparison: {
        name: 'editCset', // does this remain an option on comparison, or become (optionally) independent
      },
    }
   */
  const theme = useTheme();
  const [open, setOpen] = React.useState(false);

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBarForDrawer position="fixed" open={open}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleDrawerOpen}
            edge="start"
            sx={{ mr: 2, ...(open && { display: 'none' }) }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            Persistent drawer
          </Typography>
        </Toolbar>
      </AppBarForDrawer>
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="persistent"
        anchor="left"
        open={open}
      >
        <DrawerHeader>
          <IconButton onClick={handleDrawerClose}>
            {theme.direction === 'ltr' ? <ChevronLeftIcon /> : <ChevronRightIcon />}
          </IconButton>
        </DrawerHeader>
        <Divider />
        <List>
          {['Inbox', 'Starred', 'Send email', 'Drafts'].map((text, index) => (
            <ListItem key={text} disablePadding>
              <ListItemButton>
                <ListItemIcon>
                  {index % 2 === 0 ? <InboxIcon /> : <MailIcon />}
                </ListItemIcon>
                <ListItemText primary={text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Divider />
        <List>
          {['All mail', 'Trash', 'Spam'].map((text, index) => (
            <ListItem key={text} disablePadding>
              <ListItemButton>
                <ListItemIcon>
                  {index % 2 === 0 ? <InboxIcon /> : <MailIcon />}
                </ListItemIcon>
                <ListItemText primary={text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>
      <Main open={open}>
        <DrawerHeader />
        {children}
      </Main>
    </Box>
  );
}









const _pages = [
  {name: 'Cset search', href: '/OMOPConceptSets'},
  {name: 'Cset comparison', href: '/cset-comparison'},
  {name: 'Example comparison', href: '/testing'},
  // {name: 'Upload CSV', href: '/upload-csv', noSearch: true, },
  // TODO: re-add Download (CSets, bundles, json...) at some point
  //{name: 'Download CSet JSON', href: '/download-json', noSearch: true, },
  {name: 'Help / About', href: '/about'}
];
function getPages(props) {
  let pages = cloneDeep(_pages);
  if (!props.codeset_ids.length) {
    let page = pages.find(d=>d.href=='/cset-comparison');
    page.disable = true;
    page.tt = 'Select one or more concept sets in order to view, compare, or edit them.'
  }
  return pages;
}
const settings = ['About'];

/* https://mui.com/material-ui/react-app-bar/ */
const MuiAppBar = (props) => {
  const location = useLocation();
  const {search} = location;
  const pages = getPages(props);

  const [anchorElNav, setAnchorElNav] = React.useState(null);
  const [anchorElUser, setAnchorElUser] = React.useState(null);

  const handleOpenNavMenu = (event) => {
    setAnchorElNav(event.currentTarget);
    console.log(anchorElNav)
  };
  const handleOpenUserMenu = (event) => {
    setAnchorElUser(event.currentTarget);
    console.log(anchorElUser)
  };
  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };
  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };
  let hamburgerMenu = (
      <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
        <IconButton
            size="large"
            aria-label="account of current user"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleOpenNavMenu}
            color="inherit"
        >
          <MenuIcon />
        </IconButton>
        <Menu
            /* This menu appears as a hamburger dropdown when the page is too narrow for the
                horizontal menu items */
            id="menu-appbar"
            anchorEl={anchorElNav}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'left',
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'left',
            }}
            open={Boolean(anchorElNav)}
            onClose={handleCloseNavMenu}
            sx={{
              display: { xs: 'block', md: 'none' },
            }}
        >
          {pages.map((page) => (
              <MenuItem key={page.name}
                        component={NavLink}
                        to={`${page.href}${page.noSearch ? '' : search}`}
                        onClick={handleCloseNavMenu}>
                <Typography textAlign="center">{page.name}</Typography>
              </MenuItem>
          ))}
        </Menu>
      </Box>
  )
  let horizontalMenu = (
      <Box /* This is the main, horizontal menu */
          sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }} >
        {pages.map((page) => {
          let button = (
              <Button
                  disabled={page.disable}
                  key={page.name}
                  // selected={page.href === window.location.pathname}
                  component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
                  variant={page.href === window.location.pathname ? 'contained' : 'text'} // so, this instead
                  to={`${page.href}${page.noSearch ? '' : search}`}
                  onClick={handleCloseNavMenu}
                  sx={{ my: 2, color: 'white', display: 'block' }}
              >
                {
                  page.name
                }
              </Button>
          );
          if (page.tt) {
            button = (
                <Tooltip title={page.tt} key={page.name}>
                  <div>
                    {button}
                  </div>
                </Tooltip>
            );
          }
          return button;
        })}
      </Box>
  )
  return (
    <AppBar position="static"
            sx={{backgroundColor: '#1986d2',}}
    >
      <Container maxWidth="false" /* "xl" */ >
        <Toolbar disableGutters>
          <MenuBookIcon sx={{ display: { xs: 'none', md: 'flex' }, mr: 1 }} />
          <Typography
            variant="h6"
            noWrap
            component="a"
            href="/"
            sx={{
              mr: 2,
              display: { xs: 'none', md: 'flex' },
              fontFamily: 'monospace',
              fontWeight: 700,
              letterSpacing: '.3rem',
              color: 'inherit',
              textDecoration: 'none',
              marginRight: '4px',
            }}
          >
            TermHub
          </Typography>
          <Typography
              sx={{
                mr: 2,
                fontFamily: 'monospace',
                fontWeight: 700,
                color: 'inherit',
              }}
          >Version 0.1</Typography>

          {hamburgerMenu}

          <MenuBookIcon sx={{ display: { xs: 'flex', md: 'none' }, mr: 1 }} />
          <Typography
            variant="h5"
            noWrap
            component="a"
            href=""
            sx={{
              mr: 2,
              display: { xs: 'flex', md: 'none' },
              flexGrow: 1,
              fontFamily: 'monospace',
              fontWeight: 700,
              letterSpacing: '.3rem',
              color: 'inherit',
              textDecoration: 'none',
            }}
          >
            TermHub
          </Typography>

          {horizontalMenu}

          <Box sx={{ flexGrow: 0 }}>
            <Tooltip title="Open settings">
              <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
                {/*<Avatar alt="Remy Sharp" src="/static/images/avatar/2.jpg" />*/}
                <Avatar alt="TermHub" src="/static/images/termhubIcon.jpg" />
              </IconButton>
            </Tooltip>
            <Menu
              sx={{ mt: '45px' }}
              id="menu-user" /*"menu-appbar"*/
              anchorEl={anchorElUser}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorElUser)}
              onClose={handleCloseUserMenu}
            >
              {settings.map((setting) => (
                <MenuItem key={setting} onClick={handleCloseUserMenu}>
                  <Typography textAlign="center">{setting}</Typography>
                </MenuItem>
              ))}
            </Menu>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};
// export default MuiAppBar;