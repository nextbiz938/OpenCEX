//###########################################################################
//   OpenCEX Frontend configuration file. More info
//   https://polygant.notion.site/Settings-3f9e0aae880e433a9d23e76f62a4a456
//###########################################################################

const localConfig = {
  wss_url: "ws://",
  two_fa: "OpenCEXSmoke",
  project_title: "OpenCEXSmoke",
  api: {
    baseURL: "http://localhost/api/v1/",
    basePublicURL: "http://localhost/api/public/v1/",
    host: "localhost",
  },
  api_url: "http://localhost",
  api_url_plane: "localhost",
  recaptcha_site_key: "6LeIxAcTAAAAAJcZVRqyHh4FAAAAAAAAAAAA4",
  vue_v: "prod",
  site_domain: "localhost",
  host: "localhost",
  help_widget: "",
  logo: "",
  themes: [
    {
      main_color: "#2A2259",
      second_color: "#ffac2a",
      cancel_color: "#d93d47",
      login_background: "#36373c",
      login_text: "white",
      main_background: "#edf1fa",
      main_text: "#2a2259",
      input_color: "white",
      input_text: "#2a2259",
      block_color: "white",
      border_color: "#f0f0f0",
    },
    {
      main_color: "#2A2259",
      second_color: "#ffac2a",
      cancel_color: "#d93d47",
      login_background: "#36373c",
      login_text: "white",
      main_background: "#171717",
      main_text: "#888888",
      input_color: "#242424",
      input_text: "#888888",
      block_color: "#242424",
      border_color: "#353535",
    },
  ],
  socials: {
    telegram: {
      link: "opencex",
      title: "sitechange",
    },
    telegramNews: {
      link: "",
      title: "site_news",
    },
    mail: "support@localhost",
    facebook: {
      link: "polygant",
      title: "Exchange",
    },
    twitter: {
      link: "polygant",
      title: "@",
    },
  },
};

export default localConfig;
