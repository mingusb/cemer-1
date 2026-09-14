add_subdirectory(cecn/chapter_2)
add_subdirectory(cecn/chapter_3)
install(FILES README.md catalog.json DESTINATION ${EMERGENT_SHARE_DEST}/demo/LegacyModels)
install(DIRECTORY publications/MollickHazyKruegerEtAl20
    DESTINATION ${EMERGENT_SHARE_DEST}/demo/LegacyModels/publications
    FILES_MATCHING PATTERN "*.proj" PATTERN "*.md" PATTERN "*.json"
    PATTERN "*.html" PATTERN "*.css" PATTERN "*.txt" PATTERN "COPYING")
