// Publish figures to the Computor figure folder from C++.
//
// Workspaces are containers without a desktop, so a plot has nowhere to appear.
// Anything that can produce a PNG can still show one: write it into the folder
// described in docs/figures.md and the Computor VS Code extension displays it.
//
// C++ has no plotting library of its own, so this is the publishing half only.
// Render however you like — a gnuplot pipe, matplotplusplus, your own
// rasteriser — then hand the PNG over:
//
//     #include <computor_figures.hpp>
//
//     std::system("gnuplot -e \"set terminal png; set output 'plot.png';"
//                 " plot sin(x)\"");
//     computor::figures::publish("sin(x)", "plot.png");
//
// Header-only, C++17, no dependencies. Every call is a no-op when
// COMPUTOR_FIGURES_DIR is unset, so the same binary runs under grading without
// leaving figure files behind.

#ifndef COMPUTOR_FIGURES_HPP
#define COMPUTOR_FIGURES_HPP

#include <cstddef>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <ios>
#include <string>
#include <system_error>

namespace computor {
namespace figures {

/// Identifies who wrote a figure, for the `source` field of the metadata.
inline constexpr const char* kSource = "cpp";

/// The figure folder, or an empty path when publishing is switched off.
inline std::filesystem::path directory() {
  const char* configured = std::getenv("COMPUTOR_FIGURES_DIR");
  if (configured == nullptr || *configured == '\0') {
    return {};
  }
  return std::filesystem::path(configured);
}

namespace detail {

inline std::string stem(int number) {
  std::string digits = std::to_string(number);
  return "fig-" + std::string(digits.size() < 6 ? 6 - digits.size() : 0, '0') + digits;
}

/// Escapes a title for a JSON string. UTF-8 bytes pass through unchanged.
inline std::string escape(const std::string& text) {
  std::string out;
  out.reserve(text.size() + 8);
  for (unsigned char character : text) {
    switch (character) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\b': out += "\\b"; break;
      case '\f': out += "\\f"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (character < 0x20) {
          static const char* kHex = "0123456789abcdef";
          out += "\\u00";
          out += kHex[character >> 4];
          out += kHex[character & 0x0f];
        } else {
          out += static_cast<char>(character);
        }
    }
  }
  return out;
}

/// Fills a temporary file next to the target, then renames it over.
///
/// The viewer reacts to files appearing, so it must never get to read a
/// half-written PNG. A rename inside the folder is atomic. The temporary name
/// starts with a dot so it cannot be mistaken for a figure — readers match
/// fig-NNNNNN.png exactly.
template <typename Writer>
bool write_atomically(const std::filesystem::path& folder, int number,
                      const std::string& extension, Writer write) {
  const std::filesystem::path target = folder / (stem(number) + extension);
  const std::filesystem::path temporary =
      folder / ("." + stem(number) + ".tmp" + extension);

  {
    std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
    if (!stream) {
      return false;
    }
    write(stream);
    if (!stream) {
      stream.close();
      std::error_code ignored;
      std::filesystem::remove(temporary, ignored);
      return false;
    }
  }

  std::error_code error;
  std::filesystem::rename(temporary, target, error);
  if (error) {
    std::error_code ignored;
    std::filesystem::remove(temporary, ignored);
    return false;
  }
  return true;
}

}  // namespace detail

/// Publishes a figure from PNG bytes already in memory.
///
/// Metadata is written before the image because the viewer keys off the PNG:
/// by the time it sees the image, the sidecar it reads is already in place.
/// Returns false when publishing is switched off or the folder is unwritable —
/// showing a plot is a side channel and must never fail the computation.
inline bool publish(int number, const std::string& title, const void* png,
                    std::size_t size) {
  const std::filesystem::path folder = directory();
  if (folder.empty()) {
    return false;
  }

  std::error_code error;
  std::filesystem::create_directories(folder, error);

  const std::string metadata = "{\"number\":" + std::to_string(number) +
                               ",\"title\":\"" + detail::escape(title) +
                               "\",\"source\":\"" + kSource + "\"}\n";

  if (!detail::write_atomically(folder, number, ".json",
                                [&](std::ostream& out) { out << metadata; })) {
    return false;
  }
  return detail::write_atomically(folder, number, ".png", [&](std::ostream& out) {
    out.write(static_cast<const char*>(png), static_cast<std::streamsize>(size));
  });
}

/// Publishes a PNG that already exists on disk, leaving the original in place.
inline bool publish(int number, const std::string& title,
                    const std::filesystem::path& png) {
  std::ifstream source(png, std::ios::binary);
  if (!source) {
    return false;
  }
  const std::string bytes((std::istreambuf_iterator<char>(source)),
                          std::istreambuf_iterator<char>());
  return publish(number, title, bytes.data(), bytes.size());
}

/// The lowest figure number the folder is not already using, or 0 when
/// publishing is switched off.
inline int next_free_number() {
  const std::filesystem::path folder = directory();
  if (folder.empty()) {
    return 0;
  }
  int number = 1;
  std::error_code ignored;
  while (std::filesystem::exists(folder / (detail::stem(number) + ".png"), ignored)) {
    ++number;
  }
  return number;
}

/// Publishes into the next free slot and returns the figure number it took, or
/// 0 if that did not work. For programs that just want to show a plot without
/// keeping track of numbers.
inline int publish(const std::string& title, const void* png, std::size_t size) {
  const int number = next_free_number();
  return number != 0 && publish(number, title, png, size) ? number : 0;
}

/// As above, for a PNG that already exists on disk.
inline int publish(const std::string& title, const std::filesystem::path& png) {
  const int number = next_free_number();
  return number != 0 && publish(number, title, png) ? number : 0;
}

/// Is this figure still open? Deleting the PNG is how the viewer closes one, so
/// a long-running program can poll this and stop drawing into it.
inline bool is_open(int number) {
  const std::filesystem::path folder = directory();
  if (folder.empty()) {
    return false;
  }
  std::error_code ignored;
  return std::filesystem::exists(folder / (detail::stem(number) + ".png"), ignored);
}

/// Closes a figure by taking it out of the folder.
inline void withdraw(int number) {
  const std::filesystem::path folder = directory();
  if (folder.empty()) {
    return;
  }
  std::error_code ignored;
  std::filesystem::remove(folder / (detail::stem(number) + ".png"), ignored);
  std::filesystem::remove(folder / (detail::stem(number) + ".json"), ignored);
}

}  // namespace figures
}  // namespace computor

#endif  // COMPUTOR_FIGURES_HPP
