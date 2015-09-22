\NeedsTeXFormat{LaTeX2e}[2010/01/01]
\ProvidesClass{trojsten-tasks}[2015/09/08 Trojsten tasks booklet]

\RequirePackage{pgfkeys, pgfopts}

\pgfkeys{
    /TROJSTEN/.cd,
    TROJSTEN/.code = \wlog{Value '#1' given},
    TROJSTEN/.store in = \TROJSTEN@store
}

\DeclareOption{fks}{\loadSeminar{fks}}
\DeclareOption{kms}{\loadSeminar{kms}}
\DeclareOption{ksp}{\loadSeminar{ksp}}
\DeclareOption{ufo}{\loadSeminar{ufo}}
\DeclareOption{prask}{\loadSeminar{prask}}