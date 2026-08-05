\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{dgs}[2019/08/09 DeGeŠ core class]

\DeclareOption{oneside}{\PassOptionsToClass{\CurrentOption}{extarticle}}
\DeclareOption{twoside}{\PassOptionsToClass{\CurrentOption}{extarticle}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}

\ExecuteOptions{a4paper, 12pt}
\ProcessOptions\relax

\LoadClass[a4paper, 12pt]{extarticle}

\RequirePackage[
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

\RequirePackage[table]{xcolor}
\RequirePackage{tikz}
\RequirePackage{nicematrix}
\RequirePackage{amsmath}
\RequirePackage{amssymb}
\RequirePackage{mleftright}
\RequirePackage{siunitx}                                    % SI units
\RequirePackage{xparse}
\RequirePackage{enumitem}                                   % sets properties for itemize, enumerate, description...
\RequirePackage{lastpage}
\RequirePackage{wasysym}                                    % extra symbols for planets, astrology, ...
\RequirePackage{pdftexcmds}
\RequirePackage{xifthen}
\RequirePackage{verbatim}
\RequirePackage{float}
\RequirePackage{caption}                                    % fancy formatting of figure and table captions
\RequirePackage{booktabs}
\RequirePackage{titlesec}
\RequirePackage{leftidx}                                    % left subscript and superscript
\RequirePackage{afterpage}
\RequirePackage{longtable}
\RequirePackage{calc}                                       % \real{}, used by pandoc in the column
                                                            % specifications of tables with widths
\RequirePackage{graphicx}
\RequirePackage{etoolbox}
\RequirePackage{cancel}                                     % cancellation of terms in mathematical expressions
\RequirePackage{multicol}
\RequirePackage{fancyhdr}                                   % fancy header and footer
\RequirePackage{hyphenat}
\RequirePackage{nicefrac}
\RequirePackage{pifont}
\RequirePackage{chngcntr}
\RequirePackage{mathtools}
\RequirePackage[normalem]{ulem}
\RequirePackage[weather]{ifsym}
\RequirePackage{nth}
\RequirePackage{fancyvrb}                                   % fancy verbatim (currently unused)
\RequirePackage{framed}

\RequirePackage[
    shorthands=off,
    slovak,
    czech,
    german,
    french,
    polish,
    spanish,
    russian,
    english,
]{babel}
% Must precede chemmacros, which pulls in `bm`. When `bm` loads it copies the *current* math
% fonts into its bold alphabets, so with the default (Computer Modern) still in place every
% \boldsymbol -- FKS writes all vectors that way -- came out in CM instead of Minion.
% `onlymath`: we want this package for the math families (MnSymbol, and the bold alphabets `bm`
% copies below), never for text -- fonts.tex sets the text fonts from assets/fonts/ by path. Its
% text half would set \rmdefault to MinionPro-OsF, a T1-only family, and mathspec then asks for it
% under fontspec's TU encoding, which does not exist: "Font shape `TU/MinionPro-OsF/m/n' undefined,
% using `TU/lmr/m/n' instead".
\RequirePackage[minionint, mathlf, onlymath]{MinionPro}

\RequirePackage{chemmacros}
\RequirePackage[version=4]{mhchem}
\chemsetup{formula=mhchem}                                  % avoid a conflict with Russian babel
\RequirePackage{chemfig}                                    % complex chemical formulae

\RequirePackage[all]{nowidow}                               % prevent widow and orphan lines
%\RequirePackage{boolexpr}                                  % boolean expressions, switch
\RequirePackage[MnSymbol]{mathspec}                         % includes fontspec; must stay after
                                                            % chemmacros, as it makes any later
                                                            % \RequirePackage{amsmath} an error
\RequirePackage[f]{esvect}
\RequirePackage{accents}

\tolerance=1000
\emergencystretch=3pt
\hyphenpenalty=1000
\exhyphenpenalty=100

\AtBeginEnvironment{verbatim}{\setlist[trivlist]{nolistsep}}
%\newfontfamily\arabicfont[Script=Arabic]{Scheherazade}

\definecolor{colour-url}{RGB}{0, 137, 162}
\definecolor{colour-link}{RGB}{0, 137, 162}
\definecolor{orange}{RGB}{255, 128, 0}

\RequirePackage{xunicode}
\RequirePackage[autostyle]{csquotes}                        % proper localized quotation marks
%\RequirePackage{bidi}                                      % bi-directional support, keep this off unless building Parsi or Hebrew

\RequirePackage[nodisplayskipstretch]{setspace}

\RequirePackage[
    colorlinks              = true,                         % use coloured links
    linkcolor               = colour-link,                  % custom Trojsten link colour
    urlcolor                = colour-url,                   % custom Trojsten URL link colour
]{hyperref}
\RequirePackage{cleveref}                                   % clever references

% paragraph settings -- formatting paragraphs and list environments
\linespread{1.0}

\setlength{\parindent}{0cm}
\setlength{\parskip}{1em plus 0.1em}
\setlength{\arraycolsep}{2pt}

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
    leftmargin      =      50mm,
    itemsep         =       0mm,
}
\setlist[enumerate]{
    topsep          =       0mm,
    itemsep         =       0mm,
}
\setlist[itemize]{
    topsep          =       0mm,
    itemsep         =       0mm,
    leftmargin      =       8mm,
}

% Setup figure caption format and width
\captionsetup[figure]{
    format                  = hang,
    width                   = 0.9\textwidth,
    textfont                = it,
}

\emergencystretch 3em
\renewcommand{\arraystretch}{1.0}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}

\NewDocumentCommand{\passthrough}{m}{#1}
\NewExpandableDocumentCommand{\rootDirectory}{}{build}
\NewExpandableDocumentCommand{\activeDirectory}{}{<undefined>}

\NewExpandableDocumentCommand{\setRoot}{m}{%
    \RenewExpandableDocumentCommand{\rootDirectory}{}{#1}%
}

\NewExpandableDocumentCommand{\setActive}{m}{%
    \RenewExpandableDocumentCommand{\activeDirectory}{}{#1}%
}

\input{core/latex/fonts.tex}
\input{core/latex/utilities.tex}
\input{core/latex/math.tex}
\input{core/latex/hacks.tex}
\input{core/latex/symbols.tex}
\input{core/latex/siunitx.tex}
