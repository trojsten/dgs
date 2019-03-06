\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{dgs}[2018/10/02 DeGeŠ core class]

\LoadClass[12pt, twoside]{article}

\RequirePackage[
    paper                   = a4paper,
    left                    = 15mm,
    right                   = 15mm,
    top                     = 15mm,
    bottom                  = 15mm,
    headheight              = 20pt,
    headsep                 = 16pt,
    footskip                = 32pt,
    includeheadfoot,                                        % we wish to include header and footer into page dimensions
    %showframe                                              % display visual frame (must be turned off for production)
]{geometry}

\RequirePackage{amsmath}
\RequirePackage{amssymb}
\RequirePackage{siunitx}
\RequirePackage{xparse}
\RequirePackage{enumitem}
\RequirePackage{listings}
\RequirePackage{lastpage}
\RequirePackage{marvosym}
\RequirePackage{pdftexcmds}
\RequirePackage{xifthen}
\RequirePackage{verbatim}
\RequirePackage{color}
\RequirePackage{float}
\RequirePackage{caption}
\RequirePackage{booktabs}
\RequirePackage{titlesec}
\RequirePackage{afterpage}
\RequirePackage{longtable}
\RequirePackage{etoolbox}
\RequirePackage{cancel}
\RequirePackage{fancyhdr}
\RequirePackage{hyphenat}
\RequirePackage{pifont}
\RequirePackage{fancyvrb}                                   % fancy verbatim (currently unused)

\RequirePackage[all]{nowidow}
\RequirePackage{boolexpr}                                   % boolean expressions, switch
\RequirePackage[MnSymbol]{mathspec}                         % includes fontspec
\RequirePackage{accents}

\definecolor{colour-url}{RGB}{0, 137, 162}
\definecolor{colour-link}{RGB}{0, 137, 162}

\RequirePackage[
    colorlinks              = true,
    linkcolor               = colour-link,                  % custom Trojsten link colour
    urlcolor                = colour-url,                   % custom Trojsten URL link colour
]{hyperref}

\RequirePackage{polyglossia}                                % multi-language support
\RequirePackage{xunicode}
\setdefaultlanguage{slovak}

\RequirePackage[nodisplayskipstretch]{setspace}

% paragraph settings -- formatting paragraphs and list environments
\linespread{1.0}

\setlength{\parindent}{0cm}
\setlength{\parskip}{6pt}

\setstretch{1.0}

\NewDocumentCommand{\setDisplaySkips}{}{%
    \setlength{\abovedisplayskip}{10pt}%
    \setlength{\belowdisplayskip}{10pt}%
    \setlength{\abovedisplayshortskip}{4pt}%
    \setlength{\belowdisplayshortskip}{4pt}%
    \setlength{\jot}{10pt}%
}
\appto{\normalsize}{\setDisplaySkips}%
\appto{\small}{\setDisplaySkips}%
\appto{\footnotesize}{\setDisplaySkips}%
\setDisplaySkips

\setlength{\itemindent}{0pt}
\setlength{\textfloatsep}{3mm}
\setlength{\LTcapwidth}{0.8\textwidth}

% Setup enumitem options for *description*, *enumerate* and *itemize*
\setlist[description]{
    style           = multiline,
    labelindent     =       8mm,
    leftmargin      =      28mm,
    itemsep         =       0mm,
}
\setlist[enumerate]{
    topsep          =   0mm,
    itemsep         =   0mm,
}
\setlist[itemize]{
    topsep          =   0mm,
    itemsep         =   0mm,
}

% Setup figure caption format and width
\captionsetup[figure]{
    format                  = hang,
    width                   = 0.9\textwidth,
}

\renewcommand{\arraystretch}{1.0}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}

\NewDocumentCommand{\rootDirectory}{}{input}
\NewDocumentCommand{\activeDirectory}{}{<undefined>}

\input{core/tex/fonts.tex}
\input{core/tex/utilities.tex}
\input{core/tex/hacks.tex}
\input{core/tex/siunitx.tex}
