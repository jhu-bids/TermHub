// from https://mui.com/material-ui/react-app-bar/#ResponsiveAppBar.js
import MenuIcon from "@mui/icons-material/Menu";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import React from "react";
// import {Tooltip} from './Tooltip';
import MenuBookRounded from "@mui/icons-material/MenuBookRounded";
import MenuItem from "@mui/material/MenuItem";
import Tooltip from "@mui/material/Tooltip";
import { NavLink, useLocation } from "react-router-dom";

import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CssBaseline from "@mui/material/CssBaseline";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import { styled, useTheme } from "@mui/material/styles";
// import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from "@mui/material/ListItemText";
import { getPages /*ContentMenuItems, ContentItem, */ } from "./contentControl";

const drawerWidth = 240;

// const settings = ['About'];

const Main = styled("main", { shouldForwardProp: (prop) => prop !== "open" })(
  ({ theme, open }) => ({
    flexGrow: 1,
    padding: theme.spacing(3),
    transition: theme.transitions.create("margin", {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    marginLeft: `-${drawerWidth}px`,
    ...(open && {
      transition: theme.transitions.create("margin", {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.enteringScreen,
      }),
      marginLeft: 0,
    }),
  })
);

const AppBarForDrawer = styled(AppBar, {
  shouldForwardProp: (prop) => prop !== "open",
})(({ theme, open }) => ({
  transition: theme.transitions.create(["margin", "width"], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  ...(open && {
    width: `calc(100% - ${drawerWidth}px)`,
    marginLeft: `${drawerWidth}px`,
    transition: theme.transitions.create(["margin", "width"], {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
}));

const DrawerHeader = styled("div")(({ theme }) => ({
  display: "flex",
  alignItems: "center",
  padding: theme.spacing(0, 1),
  // necessary for content to be below app bar
  ...theme.mixins.toolbar,
  justifyContent: "flex-end",
}));

export function PersistentDrawerLeft(props) {
  // may come back to this. going back to top navbar for now
  const { children } = props;
  const theme = useTheme();
  const [open, setOpen] = React.useState(false);
  const location = useLocation();
  const { search } = location;
  const pages = getPages(props);

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  return (
    <Box sx={{ display: "flex" }}>
      <CssBaseline />
      <AppBarForDrawer position="fixed" open={open}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleDrawerOpen}
            edge="start"
            sx={{ mr: 2, ...(open && { display: "none" }) }}
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
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            boxSizing: "border-box",
          },
        }}
        variant="persistent"
        anchor="left"
        open={open}
      >
        <DrawerHeader>
          <IconButton onClick={handleDrawerClose}>
            {theme.direction === "ltr" ? (
              <ChevronLeftIcon />
            ) : (
              <ChevronRightIcon />
            )}
          </IconButton>
        </DrawerHeader>
        <Divider />
        <List>
          {pages.map((page) => {
            let button = (
              <ListItem key={page.name} disablePadding>
                <ListItemButton
                  disabled={page.disable}
                  component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
                  variant={
                    page.href === window.location.pathname
                      ? "contained"
                      : "text"
                  } // so, this instead
                  to={`${page.href}${page.noSearch ? "" : search}`}
                  // onClick={handleCloseNavMenu}
                  // sx={{ my: 2, color: 'white', display: 'block' }}
                >
                  <ListItemText primary={page.name} />
                  {/*
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
                    */}
                </ListItemButton>
              </ListItem>
            );
            if (page.tt) {
              button = (
                <Tooltip title={page.tt} key={page.name}>
                  <div>{button}</div>
                </Tooltip>
              );
            }
            return button;
          })}
        </List>
        <Divider />
        {/*<ContentMenuItems/>*/}
        {/*
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
        */}
      </Drawer>
      <Main open={open}>
        <DrawerHeader />
        {children}
      </Main>
    </Box>
  );
}

/* https://mui.com/material-ui/react-app-bar/ */
export default function MuiAppBar(props) {
  const location = useLocation();
  const { search } = location;
  const pages = getPages(props);

  const [anchorElNav, setAnchorElNav] = React.useState(null);
  const [anchorElUser, setAnchorElUser] = React.useState(null);

  const handleOpenNavMenu = (event) => {
    setAnchorElNav(event.currentTarget);
    console.log(anchorElNav);
  };
  const handleOpenUserMenu = (event) => {
    setAnchorElUser(event.currentTarget);
    console.log(anchorElUser);
  };
  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };
  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };
  let hamburgerMenu = (
    <Box sx={{ flexGrow: 1, display: { xs: "flex", md: "none" } }}>
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
          vertical: "bottom",
          horizontal: "left",
        }}
        keepMounted
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
        open={Boolean(anchorElNav)}
        onClose={handleCloseNavMenu}
        sx={{
          display: { xs: "block", md: "none" },
        }}
      >
        {pages.map((page) => (
          <MenuItem
            key={page.name}
            component={NavLink}
            to={`${page.href}${page.noSearch ? "" : search}`}
            onClick={handleCloseNavMenu}
          >
            <Typography textAlign="center">{page.name}</Typography>
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
  let horizontalMenu = (
    <Box /* This is the main, horizontal menu */
      sx={{ flexGrow: 1, display: { xs: "none", md: "flex" } }}
    >
      {pages.map((page) => {
        let button = (
          <Button
            disabled={page.disable}
            key={page.name}
            // selected={page.href === window.location.pathname}
            component={NavLink} // NavLink is supposed to show different if it's active; doesn't seem to be working
            variant={
              page.href === window.location.pathname ? "contained" : "text"
            } // so, this instead
            to={`${page.href}${page.noSearch ? "" : search}`}
            onClick={handleCloseNavMenu}
            sx={{ my: 2, color: "white", display: "block" }}
          >
            {page.name}
          </Button>
        );
        if (page.tt) {
          button = (
            <Tooltip title={page.tt} key={page.name}>
              <div>{button}</div>
            </Tooltip>
          );
        }
        return button;
      })}
    </Box>
  );
  return (
    <AppBar
      className="Mui-app-bar"
      position="static"
      sx={{ backgroundColor: "#1986d2" }}
    >
      <Container maxWidth="false" /* "xl" */>
        <Toolbar disableGutters>
          <MenuBookRounded sx={{ display: { xs: "none", md: "flex" }, mr: 1 }} />
          <Typography
            variant="h6"
            noWrap
            component="a"
            href="/"
            sx={{
              mr: 2,
              display: { xs: "none", md: "flex" },
              fontWeight: 700,
              letterSpacing: ".3rem",
              color: "inherit",
              textDecoration: "none",
              marginRight: "4px",
            }}
          >
            TermHub
          </Typography>
          <Typography
            sx={{
              mr: 2,
              fontWeight: 700,
              color: "inherit",
            }}
          >
            v0.1
          </Typography>

          {hamburgerMenu}

          <MenuBookRounded sx={{ display: { xs: "flex", md: "none" }, mr: 1 }} />
          <Typography
            variant="h5"
            noWrap
            component="a"
            href=""
            sx={{
              mr: 2,
              display: { xs: "flex", md: "none" },
              flexGrow: 1,
              fontFamily: "monospace",
              fontWeight: 700,
              letterSpacing: ".3rem",
              color: "inherit",
              textDecoration: "none",
            }}
          >
            TermHub
          </Typography>

          {horizontalMenu}

          {/*
          <Box sx={{ flexGrow: 0 }}>
            <Tooltip title="Open settings">
              <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
                <Avatar alt="TermHub" src="/static/images/termhubIcon.jpg" />
              </IconButton>
            </Tooltip>
            <Menu
              sx={{ mt: '45px' }}
              id="menu-user" /*"menu-appbar"* /
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
          */}
        </Toolbar>
      </Container>
    </AppBar>
  );
}
// export default MuiAppBar;
