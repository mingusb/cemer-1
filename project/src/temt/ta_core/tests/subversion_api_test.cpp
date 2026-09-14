// Standalone smoke test for the current SVN APIs used by SubversionClient.
// Build through the adjacent CMakeLists.txt to select a matching SVN/APR ABI.
// Pass an empty temporary directory as the only argument. No network is used.
#include <svn_client.h>
#include <svn_version.h>
#include <svn_dirent_uri.h>
#include <svn_pools.h>
#include <svn_repos.h>
#include <apr_strings.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void check(svn_error_t *error) {
  if (!error) return;
  std::string message = error->message ? error->message : "Subversion error";
  svn_error_clear(error);
  throw std::runtime_error(message);
}
void require(bool value, const char *message) {
  if (!value) throw std::runtime_error(message);
}
svn_error_t *message(const char **text, const char **temporary,
                     const apr_array_header_t *, void *, apr_pool_t *pool) {
  *text = apr_pstrdup(pool, "SVN API migration test");
  *temporary = nullptr;
  return SVN_NO_ERROR;
}
svn_error_t *committed(const svn_commit_info_t *info, void *baton, apr_pool_t *) {
  *static_cast<svn_revnum_t *>(baton) = info->revision;
  return SVN_NO_ERROR;
}
svn_error_t *info(void *baton, const char *, const svn_client_info2_t *item,
                  apr_pool_t *) {
  *static_cast<svn_revnum_t *>(baton) = item->last_changed_rev;
  return SVN_NO_ERROR;
}
svn_error_t *listed(void *baton, const char *, const svn_dirent_t *,
                    const svn_lock_t *, const char *, const char *, const char *,
                    apr_pool_t *) {
  ++*static_cast<int *>(baton);
  return SVN_NO_ERROR;
}
apr_array_header_t *paths(apr_pool_t *pool, const char *path) {
  auto *result = apr_array_make(pool, 1, sizeof(const char *));
  APR_ARRAY_PUSH(result, const char *) = path;
  return result;
}
void write(const std::string &path, const char *contents) {
  std::ofstream stream(path);
  stream << contents;
  require(stream.good(), "Could not write test file");
}
}

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  if (apr_initialize() != APR_SUCCESS) return 2;
  apr_pool_t *pool = svn_pool_create(nullptr);
  int status = 0;
  try {
    const std::string base = std::filesystem::absolute(argv[1]).string();
    const std::string repository = base + "/repository";
    const std::string wc = base + "/working-copy";
    const std::string original = wc + "/original.txt";
    const std::string copy = wc + "/copy.txt";
    const std::string moved = wc + "/moved.txt";
    const std::string directory = wc + "/directory";
    svn_repos_t *repos;
    check(svn_repos_create(&repos, repository.c_str(), nullptr, nullptr,
                          nullptr, nullptr, pool));
    const char *url;
    check(svn_uri_get_file_url_from_dirent(&url, repository.c_str(), pool));
    svn_client_ctx_t *ctx;
    check(svn_client_create_context2(&ctx, nullptr, pool));
    ctx->log_msg_func3 = message;
    svn_opt_revision_t head{}, working{}, base_revision{};
    head.kind = svn_opt_revision_head;
    working.kind = svn_opt_revision_working;
    base_revision.kind = svn_opt_revision_base;
    svn_revnum_t revision;
#if SVN_VER_MAJOR > 1 || (SVN_VER_MAJOR == 1 && SVN_VER_MINOR >= 15)
    check(svn_client_checkout4(&revision, url, wc.c_str(), &head, &head,
                              svn_depth_infinity, false, false,
                              nullptr, svn_tristate_unknown, ctx, pool));
#else
    check(svn_client_checkout3(&revision, url, wc.c_str(), &head, &head,
                              svn_depth_infinity, false, false, ctx, pool));
#endif
    require(revision == 0, "Empty checkout revision");
    write(original, "original\n");
    check(svn_client_add5(original.c_str(), svn_depth_empty, true, false,
                         false, true, ctx, pool));
    auto commit = [&]() {
      revision = SVN_INVALID_REVNUM;
      check(svn_client_commit6(paths(pool, wc.c_str()), svn_depth_infinity,
                              false, false, false, false, false, nullptr, nullptr,
                              committed, &revision, ctx, pool));
    };
    commit();
    require(revision == 1, "First commit callback revision");

    svn_client_copy_source_t source{original.c_str(), &working, &working};
    auto *sources = apr_array_make(pool, 1, sizeof(svn_client_copy_source_t *));
    APR_ARRAY_PUSH(sources, svn_client_copy_source_t *) = &source;
    check(svn_client_copy7(sources, copy.c_str(), false, true, true, false,
                          false, nullptr, nullptr, nullptr, nullptr, ctx, pool));
    require(std::filesystem::exists(copy), "Copy did not create the file");
    check(svn_client_move7(paths(pool, copy.c_str()), moved.c_str(), false,
                          true, true, false, nullptr, nullptr, nullptr, ctx, pool));
    require(std::filesystem::exists(moved), "Move did not create the file");
    check(svn_client_mkdir4(paths(pool, directory.c_str()), true, nullptr,
                           nullptr, nullptr, ctx, pool));
    require(std::filesystem::is_directory(directory), "Mkdir failed");

    revision = SVN_INVALID_REVNUM;
    check(svn_client_info4(original.c_str(), nullptr, nullptr, svn_depth_empty,
                          false, true, false, nullptr, info, &revision, ctx, pool));
    require(revision == 1, "Working-copy info revision");
    const char *root;
    check(svn_client_get_repos_root(&root, nullptr, original.c_str(), ctx, pool, pool));
    require(std::string(root) == url, "Repository root URL");
    int count = 0;
    check(svn_client_list4(url, &head, &head, nullptr, svn_depth_infinity,
                          SVN_DIRENT_ALL, false, false, listed, &count, ctx, pool));
    require(count == 2, "Repository listing should contain root and original");
    auto *content = svn_stringbuf_create_empty(pool);
    const std::string original_url = std::string(url) + "/original.txt";
    check(svn_client_cat3(nullptr, svn_stream_from_stringbuf(content, pool),
                         original_url.c_str(), &head, &head, true, ctx, pool, pool));
    require(std::string(content->data, content->len) == "original\n", "Cat content");

    write(original, "changed\n");
    auto *diff = svn_stringbuf_create_empty(pool);
    check(svn_client_diff7(nullptr, original.c_str(), &base_revision,
                          original.c_str(), &working, nullptr, svn_depth_infinity,
                          true, false, true, false, false, false, false, false,
                          true, "UTF-8", svn_stream_from_stringbuf(diff, pool),
                          svn_stream_empty(pool), nullptr, ctx, pool));
    require(std::string(diff->data, diff->len).find("+changed") != std::string::npos,
            "Working-copy diff did not include changed content");
    check(svn_client_revert4(paths(pool, original.c_str()), svn_depth_infinity,
                            nullptr, false, false, true, ctx, pool));
    std::ifstream reverted(original);
    std::string line;
    std::getline(reverted, line);
    require(line == "original", "Revert did not restore content");
    commit();
    require(revision == 2, "Copy/move/mkdir commit revision");
    check(svn_client_delete4(paths(pool, moved.c_str()), false, false, nullptr,
                            nullptr, nullptr, ctx, pool));
    commit();
    require(revision == 3, "Delete commit revision");
    commit();
    require(revision == SVN_INVALID_REVNUM, "No-op commit should not invoke callback");
    check(svn_client_cleanup2(wc.c_str(), true, true, true, true, false, ctx, pool));
    std::cout << "SVN modern API local-repository smoke test passed\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    status = 1;
  }
  svn_pool_destroy(pool);
  apr_terminate();
  return status;
}
