// from https://mui.com/material-ui/react-app-bar/#ResponsiveAppBar.js
import * as React from 'react';
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
import Tooltip from '@mui/material/Tooltip';
import MenuItem from '@mui/material/MenuItem';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import {NavLink, useLocation} from "react-router-dom";

const pages = [
  {name: 'Cset search', href: '/OMOPConceptSets'},
  {name: 'Cset comparison', href: '/cset-comparison'},
  {name: 'Example comparison', href: '/testing'},
  //{name: 'Upload CSV', href: '/upload-csv'},
  {name: 'About', href: '/about'}
];
const settings = ['About'];

/* https://mui.com/material-ui/react-app-bar/ */
const MuiAppBar = () => {
  const {search} = useLocation();

  const [anchorElNav, setAnchorElNav] = React.useState(null);
  const [anchorElCsets, setAnchorElCsets] = React.useState(null);
  const [anchorElUser, setAnchorElUser] = React.useState(null);

  const handleOpenNavMenu = (event) => {
    setAnchorElNav(event.currentTarget);
    console.log(anchorElNav)
  };
  const handleOpenUserMenu = (event) => {
    setAnchorElUser(event.currentTarget);
    console.log(anchorElUser)
  };
  const handleOpenCsetsMenu = (event) => {
    setAnchorElCsets(event.currentTarget);
    console.log(anchorElCsets)
  };
  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };
  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };
  const handleCloseCsetsMenu = () => {
    setAnchorElCsets(null);
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
                        to={`${page.href}${search}`}
                        onClick={handleCloseNavMenu}>
                <Typography textAlign="center">{page.name}</Typography>
              </MenuItem>
          ))}
        </Menu>
      </Box>
  )
  let junk = (<div id="JUNK">
    <Button
        key="testing0"
        href="/about"
        onClick={handleCloseNavMenu}
        sx={{ my: 2, color: 'white', display: 'block' }}
    >
      Testing0
    </Button>
    {/*
        tried to add menu items for individual csets that are or have been opened, gave up
        if interested in trying again, learn more about menus (or some other component):
          https://mui.com/material-ui/api/menu/
          https://mui.com/material-ui/react-menu/
    */}
    <Button key="csets"
            size="large"
            aria-label="list of csets to revisit"
            aria-controls="past-csets"
            aria-haspopup="true"
            onClick={handleOpenCsetsMenu}
            color="inherit" >
      Concept set
    </Button>
    <Menu
        /* trying to add menu items for individual csets that are or have been opened */
        id="past-csets"
        anchorEl={anchorElCsets}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        open={Boolean(anchorElCsets)}
        onClose={handleCloseCsetsMenu}
        sx={{
          display: { xs: 'block', md: 'none' },
        }}
    >
      <MenuItem /*key={page.name} component={Link} to={page.href} onClick={handleCloseCsetsMenu} */>
        <Typography textAlign="left">{/*page.name*/}
          testing 1
        </Typography>
      </MenuItem>
      <MenuItem>
        <Typography textAlign="left">testing2</Typography>
      </MenuItem>
    </Menu>
  </div>)
  let horizontalMenu = (
      <Box /* This is the main, horizontal menu */
          sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }} >
        {pages.map((page) => (
            <Button
                key={page.name}
                component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
                to={`${page.href}${search}`}
                onClick={handleCloseNavMenu}
                sx={{ my: 2, color: 'white', display: 'block' }}
            >
              {page.name}
            </Button>
        ))}
        {/* junk */}
      </Box>
  )
  return (
    <AppBar position="static">
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
