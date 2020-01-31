#ifndef _A_H_
#define _A_H_

#ifdef WIN32
#ifdef A_EXPORTS
#define A_API __declspec(dllexport)
#else
#define A_API __declspec(dllimport)    
#endif
#else
#define A_API    
#endif


int A_API add(int a, int b);

#endif