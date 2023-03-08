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
export default MuiAppBar;
