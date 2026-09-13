// Check blend lane selection and zero masking on both SSE2 and SSE4.1.
// Build with: clang++ -std=c++17 -Wall -Wextra -Werror -msse2 vector_blend_test.cpp
#include "../vectorclass.h"
#include <stdexcept>
template<int a,int b,int c,int d> void verify() {
  const int indices[4]={a,b,c,d};
  const int source[8]={11,22,33,44,55,66,77,88};
  Vec4i first(11,22,33,44), second(55,66,77,88);
  auto result=blend4i<a,b,c,d>(first,second);
  int actual[4]; result.store(actual);
  for(int i=0;i<4;++i) {
    if (actual[i] != (indices[i]<0?0:source[indices[i]]))
      throw std::runtime_error("SIMD blend lane did not match scalar result");
  }
}
int main() {
#if INSTRSET >= 5 && (defined(__GNUC__) || defined(__clang__))
 if (!__builtin_cpu_supports("sse4.1")) return 77;
#endif
 verify<0,1,2,3>();verify<4,5,6,7>();verify<0,4,1,5>();verify<4,0,5,1>();
 verify<2,6,3,7>();verify<6,2,7,3>();verify<1,2,3,4>();verify<5,6,7,0>();
 verify<-1,4,1,5>();verify<0,-1,2,7>();verify<-1,2,3,4>();verify<-1,6,7,0>();
 verify<0,5,2,7>();verify<6,1,4,3>();verify<-1,-1,-1,-1>();
}
